"""Research runner: builds inputs once, runs sleeve/portfolio variants, and logs every trial.

Every call to `evaluate` appends a row to data/results/trials.csv (config, window, Sharpe).
The deflated Sharpe ratio is computed from that ledger, so the number of variants tried is
recorded mechanically rather than remembered. The holdout window (config.HOLDOUT_START
onward) is refused unless `unseal=True`, and each unsealing is itself logged.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import backtest, metrics, panel, prices, screens, signals, sleeves
from .config import DATA, HOLDOUT_START
from .freight import load as load_freight
from .universe import deal_frozen, tradable

RESULTS = DATA / "results"


class Inputs:
    def __init__(self):
        p = panel.build()
        self.p = p
        self.tr = p.total_return
        self.seg = tradable().set_index("id")["segment"]
        self.inv = screens.investable(p, frozen=deal_frozen(self.tr.index))
        self.adv = screens.median_adv(p.dollar_volume).shift(1)
        self.vol = self.tr.rolling(63, min_periods=20).std().shift(0)
        self.btm, self.strength, self.mcap = signals.value_and_strength(p)
        self.fr = load_freight()
        self.spy = prices.total_return(prices.load("yahoo", "SPY")).reindex(self.tr.index)
        self.bf, self.resid = signals.freight_model(p, self.fr, self.spy)
        self.bm = self._market_beta()
        self.logp = np.log((1 + self.tr.fillna(0)).cumprod()).where(self.tr.notna())

    def _market_beta(self, window=252):
        m = self.spy
        cov = self.tr.rolling(window, min_periods=126).cov(m)
        var = m.rolling(window, min_periods=126).var()
        return cov.div(var, axis=0).clip(-1, 3)


def factor_z(inp: Inputs, fmom_lookback: int = 63, strength_regime: bool = False):
    """Within-segment z-scores. With strength_regime, balance-sheet strength is held long
    when the segment's freight momentum is negative and short (i.e. leverage held long)
    when it is positive: the 'balance sheet as the option strike' hypothesis."""
    fm = signals.freight_momentum(inp.fr, inp.tr, fmom_lookback)
    fmom_score = inp.bf * fm
    z_v = signals.zscore_within(inp.btm, inp.inv, inp.seg)
    z_s = signals.zscore_within(inp.strength, inp.inv, inp.seg)
    if strength_regime:
        z_s = z_s * (-np.sign(fm)).reindex_like(z_s)
    z_f = signals.zscore_within(fmom_score, inp.inv, inp.seg)
    return z_v, z_s, z_f


def _guard(end):
    if end is None or pd.Timestamp(end) >= pd.Timestamp(HOLDOUT_START):
        raise PermissionError("Holdout is sealed: pass end < HOLDOUT_START or unseal=True")


def log_trial(name: str, config: dict, start, end, r: pd.Series, tag: str = "research",
              periods_per_year: int = 252):
    """Append one run to the ledger. Monthly series: pass periods_per_year=12; the stored
    daily-equivalent Sharpe is then SR_period / sqrt(252 / periods_per_year)."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    s = metrics.summary(r) if periods_per_year == 252 else {}
    sr_p = r.mean() / r.std() if r.std() > 0 else np.nan
    if periods_per_year != 252:
        eq = (1 + r).prod()
        s = {"sharpe": sr_p * np.sqrt(periods_per_year), "ann_return": eq ** (periods_per_year / len(r)) - 1,
             "ann_vol": r.std() * np.sqrt(periods_per_year), "max_drawdown": metrics.drawdown(r).min()}
    row = {"time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tag": tag,
           "name": name, "start": str(start), "end": str(end), "config": json.dumps(config, default=str),
           "sharpe": s.get("sharpe"), "daily_sharpe": sr_p / np.sqrt(252 / periods_per_year),
           "ann_return": s.get("ann_return"), "ann_vol": s.get("ann_vol"), "max_dd": s.get("max_drawdown")}
    path = RESULTS / "trials.csv"
    pd.DataFrame([row]).to_csv(path, mode="a", header=not path.exists(), index=False)
    return s


def build_targets(inp: Inputs, start, end, fp=None, rpar=None, pp=None, fmom_lookback=63,
                  which=("pairs", "factor", "residual"), strength_regime=False):
    fp = fp or sleeves.FactorParams()
    rpar = rpar or sleeves.ResidualParams()
    pp = pp or sleeves.PairsParams()
    idx = inp.tr.loc[start:end].index
    dates = sleeves.rebalance_dates(idx)
    out = {}
    if "factor" in which:
        z_v, z_s, z_f = factor_z(inp, fmom_lookback, strength_regime)
        out["factor"] = sleeves.factor_sleeve(z_v, z_s, z_f, inp.inv, inp.seg, inp.vol, dates, fp)
    if "residual" in which:
        rz = signals.residual_z(inp.resid, horizon=rpar.horizon)
        out["residual"] = sleeves.residual_sleeve(rz, inp.inv, inp.seg, inp.vol, dates, rpar)
    if "pairs" in which:
        out["pairs"] = sleeves.pairs_sleeve(inp.logp, inp.tr, inp.inv, inp.seg, inp.strength, idx, pp)
    return out


def evaluate(inp: Inputs, targets: dict, start, end, rp=None, name="portfolio", config=None,
             unseal=False):
    if not unseal:
        _guard(end)
    else:
        RESULTS.mkdir(parents=True, exist_ok=True)
        with open(RESULTS / "holdout_unsealed.log", "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} unsealed for {name} {start}..{end}\n")
    rp = rp or backtest.RiskParams()
    res = backtest.run(targets, inp.tr, inp.inv, inp.adv, inp.vol, inp.bm, inp.spy, rp, start, end)
    cfg = dict(config or {}, risk=asdict(rp), sleeves=list(targets))
    log_trial(name, cfg, start, end, res.returns, tag="holdout" if unseal else "research")
    return res


def walk_forward(config_returns: dict[str, pd.Series], first_year: int, last_year: int,
                 min_history_years: int = 3) -> pd.Series:
    """For each year Y, pick the config with the best Sharpe on all data before Y.

    config_returns must be computed causally (returns at t use information up to t only),
    which holds for every sleeve in this project. Returns {year: chosen config}.
    """
    picks = {}
    for y in range(first_year, last_year + 1):
        best, best_s = None, -np.inf
        for k, r in config_returns.items():
            h = r.loc[: f"{y - 1}-12-31"].dropna()
            h = h[h.ne(0).cumsum() > 0]          # from the first active day
            if len(h) < 252 * min_history_years or h.std() == 0:
                continue
            s = h.mean() / h.std()
            if s > best_s:
                best, best_s = k, s
        picks[y] = best
    return pd.Series(picks)
