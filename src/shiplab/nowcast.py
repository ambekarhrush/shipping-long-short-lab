"""Freight nowcasting: can port-call, chokepoint and equity data say where freight goes next?

Target: log change of a Baltic index over the next four weeks, sampled every Friday.
Every feature uses only information published by that Friday (PortWatch is lagged one week to
allow for its publication delay). Models are refit every week on an expanding window and
scored strictly out of sample from 2021, against two benchmarks:

* random walk (forecast = no change), the standard bar for freight;
* momentum only (the index's own recent changes), so the alternative data has to add
  something beyond what is visible in the freight index itself.

The ridge penalty is fixed in advance (alpha = 10 on standardised features) rather than tuned,
so the out-of-sample score is not flattered by a search.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import freight, panel
from .config import CACHE
from .universe import tradable

TARGETS = {"BDI": "dry_bulk", "BCI": "dry_bulk", "BDTI": "tankers", "BCTI": "tankers", "BLPG": "gas"}
HORIZON = 4
OOS_START = "2021-01-01"
ALPHA = 10.0
PW_LAG = 1  # weeks
# Compact port/chokepoint sets, one per segment, fixed in advance. A first version fed every
# chokepoint and country series (about 20 features) and overfit badly out of sample (capesize
# out-of-sample R^2 of -2.1); that result is reported in 02-freight-priced-by-friday/README.md.
PORTS = {
    "dry_bulk": ["pw_db_cape_share_d4", "pw_db_malacca_d4", "pw_dry_exports_d4"],
    "tankers": ["pw_tk_cape_share_d4", "pw_tk_hormuz_d4", "pw_tk_malacca_d4"],
    "gas": ["pw_tk_cape_share_d4", "pw_tk_hormuz_d4"],
}


def _w(x: pd.DataFrame | pd.Series):
    return x.resample("W-FRI")


def features() -> pd.DataFrame:
    """Weekly feature panel (columns prefixed by family) and freight log levels."""
    fr = np.log(freight.load()).ffill()
    wf = _w(fr).last()
    out = {}
    for s in wf.columns:  # own momentum
        out[f"mom1_{s}"] = wf[s].diff(1)
        out[f"mom4_{s}"] = wf[s].diff(4)
        out[f"mom12_{s}"] = wf[s].diff(12)

    c = pd.read_parquet(CACHE / "portwatch" / "chokepoints.parquet")
    for col, tag in [("capacity_tanker", "tk"), ("capacity_dry_bulk", "db"), ("capacity_container", "ct")]:
        p = c.pivot_table(index="date", columns="chokepoint", values=col, aggfunc="sum")
        p = _w(p).sum().shift(PW_LAG)
        cape = p["Cape of Good Hope"] / (p["Cape of Good Hope"] + p["Suez Canal"] + 1)
        out[f"pw_{tag}_cape_share_d4"] = cape.diff(4)
        for k, short in [("Strait of Hormuz", "hormuz"), ("Malacca Strait", "malacca"), ("Panama Canal", "panama"),
                         ("Bab el-Mandeb Strait", "babelmandeb"), ("Bosporus Strait", "bosporus")]:
            out[f"pw_{tag}_{short}_d4"] = np.log(p[k].replace(0, np.nan)).diff(4)

    for f in sorted((CACHE / "portwatch" / "by_country").glob("*.parquet")):
        d = pd.read_parquet(f).assign(date=lambda z: pd.to_datetime(z.date)).set_index("date").sort_index()
        iso = f.stem
        for col in ("export_dry_bulk", "export_tanker"):
            x = _w(d[col]).sum().shift(PW_LAG)
            out[f"pw_{iso}_{col}_d4"] = np.log(x.replace(0, np.nan)).rolling(4).mean().diff(4)

    ex = [out[k] for k in list(out) if k.endswith("export_dry_bulk_d4")]
    out["pw_dry_exports_d4"] = pd.concat(ex, axis=1).mean(axis=1)

    p = panel.build()
    seg = tradable().set_index("id")["segment"]
    r = p.total_return
    for s in ("dry_bulk", "tankers", "gas"):
        names = [c for c in r.columns if seg.get(c) == s]
        b = np.log1p(r[names].mean(axis=1).fillna(0)).cumsum()
        out[f"eq_{s}_d1"] = _w(b).last().diff(1)
        out[f"eq_{s}_d4"] = _w(b).last().diff(4)
    X = pd.DataFrame(out).replace([np.inf, -np.inf], np.nan)
    return X.loc["2019-06":], wf.loc["2019-06":]


def _ridge(X: np.ndarray, y: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
    mu, sd = X.mean(0), X.std(0) + 1e-12
    Z = (X - mu) / sd
    b = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return b / sd, y.mean() - (mu / sd) @ b


def run(min_train: int = 104) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Walk-forward forecasts for each target; returns (forecasts, scores, latest nowcast)."""
    X, wf = features()
    rows, latest = [], []
    for sym, segm in TARGETS.items():
        y = wf[sym].shift(-HORIZON) - wf[sym]
        own = [f"mom1_{sym}", f"mom4_{sym}", f"mom12_{sym}"]
        alt = PORTS[segm]
        eq = [f"eq_{segm}_d1", f"eq_{segm}_d4"]
        sets = {"momentum": own, "momentum+ports": own + alt, "momentum+equities": own + eq,
                "all": own + alt + eq}
        dates = X.index[X.index >= OOS_START]
        for d in dates:
            # train only on targets fully realised by d (y at t needs t+HORIZON <= d)
            tr_end = d - pd.Timedelta(weeks=HORIZON)
            for name, cols in sets.items():
                D = pd.concat([X[cols], y.rename("y")], axis=1)
                tr = D.loc[:tr_end].dropna()
                if len(tr) < min_train or d not in D.index or D.loc[d, cols].isna().any():
                    continue
                b, a = _ridge(tr[cols].values, tr["y"].values, ALPHA)
                rows.append({"target": sym, "model": name, "date": d,
                             "forecast": float(D.loc[d, cols].values @ b + a), "actual": y.get(d)})
        # latest nowcast with all data (actual unknown)
        d = X.index[-1]
        for name, cols in sets.items():
            D = pd.concat([X[cols], y.rename("y")], axis=1)
            tr = D.loc[: d - pd.Timedelta(weeks=HORIZON)].dropna()
            row = X.loc[d, cols]
            if row.isna().any():
                row = X[cols].ffill().iloc[-1]
            b, a = _ridge(tr[cols].values, tr["y"].values, ALPHA)
            latest.append({"target": sym, "model": name, "as_of": d.date(), "forecast_4w_logchg": float(row.values @ b + a)})
    fc = pd.DataFrame(rows)
    sc = score(fc)
    return fc, sc, pd.DataFrame(latest)


def score(fc: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (sym, m), g in fc.dropna(subset=["actual"]).groupby(["target", "model"]):
        e = g.actual - g.forecast
        r2 = 1 - (e ** 2).sum() / (g.actual ** 2).sum()            # vs random walk (zero change)
        hit = (np.sign(g.forecast) == np.sign(g.actual)).mean()
        out.append({"target": sym, "model": m, "weeks": len(g), "oos_r2_vs_random_walk": r2,
                    "direction_hit_rate": hit, "corr": g.forecast.corr(g.actual)})
    s = pd.DataFrame(out)
    base = s[s.model == "momentum"].set_index("target")["oos_r2_vs_random_walk"]
    s["r2_gain_vs_momentum"] = s.oos_r2_vs_random_walk - s.target.map(base)
    return s
