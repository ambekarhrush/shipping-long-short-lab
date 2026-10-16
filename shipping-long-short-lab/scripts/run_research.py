"""Reproduce every research result from raw data into data/results/.

    uv run python scripts/run_research.py            # development + validation (2011-2022)
    uv run python scripts/run_research.py --holdout  # also re-run the pre-registered holdout

Reproduction runs are logged in the trials ledger with tag 'reproduce' and are excluded from
the deflated-Sharpe trial count (which counts only distinct research variants).
"""

from __future__ import annotations

import argparse
import itertools
import json
import pickle
import warnings

import numpy as np
import pandas as pd

from shiplab import backtest, metrics, prices, research, signals, sleeves
from shiplab.config import DATA

warnings.filterwarnings("ignore")
OUT = DATA / "results"
S0, WF0, VAL0, DEV_END, VAL_END = "2011-01-01", 2014, "2021-01-01", "2020-12-31", "2022-12-31"
HS, HE = "2023-01-01", None
STRESS = {
    "2016 dry bulk trough": ("2015-11-01", "2016-06-30"),
    "COVID shock": ("2020-02-15", "2020-05-31"),
    "2022 Russia sanctions": ("2022-02-24", "2022-12-31"),
    "Red Sea disruption": ("2023-11-15", "2024-12-31"),
    "2026 Hormuz crisis": ("2026-02-28", None),
}


def grid():
    g = {}
    for q, w in itertools.product((1 / 3, 1 / 2), ((1, 0, 0), (1, 1, 1), (1, 0, 1))):
        g[f"factor|q={q:.2f}|w={w}"] = ("factor", dict(fp=sleeves.FactorParams(quantile=q, weights=w)))
    for ent, hz in itertools.product((0.75, 1.0, 1.5), (10, 20)):
        g[f"residual|entry={ent}|h={hz}"] = ("residual", dict(rpar=sleeves.ResidualParams(entry=ent, horizon=hz)))
    for ent, mc in itertools.product((1.5, 2.0), (0.5, 0.6)):
        g[f"pairs|entry={ent}|corr={mc}"] = ("pairs", dict(pp=sleeves.PairsParams(entry=ent, min_corr=mc)))
    return g


def segment_attribution(res, tr, seg):
    held = res.weights
    r = tr.reindex(held.index).fillna(0)
    rows = {}
    for s in seg.unique():
        cols = [c for c in held.columns if seg.get(c) == s]
        rows[(s, "long")] = (held[cols].clip(lower=0) * r[cols]).sum(axis=1)
        rows[(s, "short")] = (held[cols].clip(upper=0) * r[cols]).sum(axis=1)
    rows[("hedge", "SPY")] = res.attribution["hedge"]
    return pd.DataFrame(rows)


def main(holdout: bool):
    OUT.mkdir(parents=True, exist_ok=True)
    inp = research.Inputs()
    rp = backtest.RiskParams(aum=10e6)
    end = HE or str(inp.tr.index[-1].date())

    # 1. grid of sleeve variants on 2011-2022 (causal), walk-forward selection
    targets, rets = {}, {}
    for k, (sl, kw) in grid().items():
        T = research.build_targets(inp, S0, VAL_END, which=(sl,), **kw)
        r = backtest.run(T, inp.tr, inp.inv, inp.adv, inp.vol, inp.bm, inp.spy, rp, S0, VAL_END)
        research.log_trial(f"WF_{k}", {"grid": k}, S0, VAL_END, r.returns, tag="reproduce")
        targets[k], rets[k] = T[sl], r.returns
    pd.DataFrame(rets).to_parquet(OUT / "grid_returns.parquet")
    picks = pd.DataFrame({sl: research.walk_forward({k: v for k, v in rets.items() if k.startswith(sl)},
                                                    WF0, 2022) for sl in ("factor", "residual", "pairs")})
    picks.to_csv(OUT / "walk_forward_picks.csv")
    stitched = {sl: pd.concat([targets[k].loc[f"{y}-01-01":f"{y}-12-31"] for y, k in picks[sl].items() if k])
                for sl in picks.columns}
    wf_all = backtest.run(stitched, inp.tr, inp.inv, inp.adv, inp.vol, inp.bm, inp.spy, rp, f"{WF0}-01-01", VAL_END)
    core = {k: v for k, v in stitched.items() if k != "pairs"}
    wf = backtest.run(core, inp.tr, inp.inv, inp.adv, inp.vol, inp.bm, inp.spy, rp, f"{WF0}-01-01", VAL_END)

    # 2. capacity and cost sensitivity (design unchanged)
    cap = []
    for aum in (2e6, 5e6, 10e6, 25e6, 50e6, 100e6, 250e6):
        r = backtest.run(core, inp.tr, inp.inv, inp.adv, inp.vol, inp.bm, inp.spy,
                         backtest.RiskParams(aum=aum), f"{WF0}-01-01", VAL_END)
        s = metrics.summary(r.returns)
        cap.append({"aum_musd": aum / 1e6, "sharpe": s["sharpe"], "ann_return": s["ann_return"],
                    "ann_vol": s["ann_vol"], "avg_gross": r.weights.abs().sum(axis=1).mean(),
                    "alpha_musd_per_year": s["ann_return"] * aum / 1e6})
    pd.DataFrame(cap).to_csv(OUT / "capacity.csv", index=False)

    # 3. holdout (pre-registered configuration)
    ho = None
    if holdout:
        T = research.build_targets(inp, S0, end, fp=sleeves.FactorParams(quantile=1 / 3, weights=(1, 0, 1)),
                                   rpar=sleeves.ResidualParams(entry=0.75, horizon=10), which=("factor", "residual"))
        T = {k: v.loc[HS:end] for k, v in T.items()}
        ho = backtest.run(T, inp.tr, inp.inv, inp.adv, inp.vol, inp.bm, inp.spy, rp, HS, end)

    # 4. benchmarks, stress, attribution, exposures
    ew = inp.tr.where(inp.inv).mean(axis=1)
    bask = signals.segment_baskets(inp.tr.where(inp.inv), inp.seg)
    bench = pd.DataFrame({"EW shipping basket": ew, "SPY": inp.spy,
                          "BDRY": prices.total_return(prices.load("yahoo", "BDRY")).reindex(inp.tr.index),
                          "BWET": prices.total_return(prices.load("yahoo", "BWET")).reindex(inp.tr.index)})
    for s in bask.columns:
        bench[f"{s} basket"] = bask[s]
    strat = wf.returns if ho is None else pd.concat([wf.returns, ho.returns])
    sleeves_r = wf.sleeve_returns if ho is None else pd.concat([wf.sleeve_returns, ho.sleeve_returns])
    pd.DataFrame({"strategy": strat, "with_pairs": wf_all.returns.reindex(strat.index)}).join(
        sleeves_r.add_prefix("sleeve_")).to_parquet(OUT / "strategy_returns.parquet")
    bench.to_parquet(OUT / "benchmark_returns.parquet")
    periods = {"Walk-forward 2014-2020": (f"{WF0}-01-01", DEV_END), "Validation 2021-2022": (VAL0, VAL_END),
               "Holdout 2023-": (HS, end)}
    rows = []
    for pname, (a, b) in periods.items():
        if ho is None and pname.startswith("Holdout"):
            continue
        for name, series in [("Strategy", strat)] + list(bench.items()):
            s = metrics.summary(series.loc[a:b].dropna(), inp.spy)
            rows.append({"period": pname, "series": name, **s})
    pd.DataFrame(rows).to_csv(OUT / "performance_by_period.csv", index=False)
    srows = []
    for nm, (a, b) in STRESS.items():
        for name, series in [("Strategy", strat), ("EW shipping basket", ew), ("SPY", inp.spy)]:
            x = series.loc[a:b].dropna()
            if len(x) > 5:
                srows.append({"window": nm, "series": name, "total_return": (1 + x).prod() - 1,
                              "max_drawdown": metrics.drawdown(x).min()})
    pd.DataFrame(srows).to_csv(OUT / "stress.csv", index=False)
    att = segment_attribution(wf, inp.tr, inp.seg)
    if ho is not None:
        att = pd.concat([att, segment_attribution(ho, inp.tr, inp.seg)])
    att.columns = [f"{a}|{b}" for a, b in att.columns]
    att.to_parquet(OUT / "attribution.parquet")
    expo = []
    for r_ in [wf] + ([ho] if ho is not None else []):
        expo.append(pd.DataFrame({"gross": r_.weights.abs().sum(axis=1),
                                  "net": r_.weights.sum(axis=1),
                                  "beta_before_hedge": (r_.weights * inp.bm.reindex(r_.weights.index)).sum(axis=1),
                                  "hedge": r_.hedge}))
    pd.concat(expo).to_parquet(OUT / "exposures.parquet")

    # 5. deflated Sharpe from the research ledger
    led = pd.read_csv(OUT / "trials.csv")
    rr = led[led.tag == "research"]
    dsr = {}
    for pname, (a, b) in periods.items():
        x = strat.loc[a:b].dropna()
        if len(x) > 60:
            dsr[pname] = metrics.deflated_sharpe(x, len(rr), rr["daily_sharpe"].std())
    json.dump({"n_research_trials": int(len(rr)), "deflated_sharpe_probability": dsr},
              open(OUT / "deflated_sharpe.json", "w"), indent=1)

    # 6. lead-lag freight vs equity (weekly)
    W = lambda s: s.resample("W-FRI").last()  # noqa: E731
    ll = {}
    for seg, sym in [("dry_bulk", "BDI"), ("tankers", "BDTI"), ("gas", "BLPG")]:
        e = W(np.log1p(bask[seg].fillna(0)).cumsum()).diff()
        f = W(np.log(inp.fr[sym])).diff()
        d = pd.concat([e, f], axis=1, keys=["eq", "fr"]).loc["2011":VAL_END].dropna()
        ll[seg] = {k: d["eq"].corr(d["fr"].shift(-k)) for k in range(-8, 9)}
    pd.DataFrame(ll).rename_axis("lag_weeks_equity_leads").to_csv(OUT / "lead_lag.csv")
    # 7. aggregate AIS (PortWatch chokepoints) vs next-month freight
    from shiplab import portwatch
    c = portwatch.chokepoints()
    piv = lambda col: c.pivot_table(index="date", columns="chokepoint", values=col, aggfunc="sum").resample("W-FRI").sum()  # noqa: E731
    tk, db = piv("capacity_tanker"), piv("capacity_dry_bulk")
    wf_ = inp.fr.resample("W-FRI").last()
    tests = {"tanker Cape share": (tk["Cape of Good Hope"] / (tk["Cape of Good Hope"] + tk["Suez Canal"]), "BDTI", False),
             "tanker Hormuz tonnes": (tk["Strait of Hormuz"], "BDTI", True),
             "dry bulk Cape share": (db["Cape of Good Hope"] / (db["Cape of Good Hope"] + db["Suez Canal"]), "BDI", False),
             "dry bulk Malacca tonnes": (db["Malacca Strait"], "BDI", True)}
    rows = []
    for nm, (x, sym, logx) in tests.items():
        x4 = np.log(x.replace(0, np.nan)).diff(4) if logx else x.diff(4)
        f = np.log(wf_[sym])
        d = pd.concat([x4, f.diff(4), f.diff(4).shift(-4)], axis=1, keys=["x", "now", "next"]).loc["2019-06":].dropna()
        rows.append({"signal": nm, "freight": sym, "corr_same_4w": d.x.corr(d.now), "corr_next_4w": d.x.corr(d.next), "weeks": len(d)})
    pd.DataFrame(rows).to_csv(OUT / "portwatch_vs_freight.csv", index=False)

    pickle.dump({"wf": wf, "ho": ho}, open(DATA / "cache" / "results.pkl", "wb"))
    print("done", {k: round(v, 3) for k, v in dsr.items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true")
    main(ap.parse_args().holdout)
