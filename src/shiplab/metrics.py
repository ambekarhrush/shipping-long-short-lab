"""Performance statistics, including the deflated Sharpe ratio (Bailey & Lopez de Prado, 2014)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

ANN = 252


def summary(r: pd.Series, bench: pd.Series | None = None) -> dict:
    r = r.dropna()
    if len(r) < 20:
        return {}
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    yrs = len(r) / ANN
    out = {
        "ann_return": eq.iloc[-1] ** (1 / yrs) - 1,
        "ann_vol": r.std() * np.sqrt(ANN),
        "sharpe": r.mean() / r.std() * np.sqrt(ANN) if r.std() > 0 else np.nan,
        "max_drawdown": dd.min(),
        "hit_rate_monthly": ((1 + r).resample("ME").prod() - 1).gt(0).mean(),
        "skew": r.skew(), "kurtosis": r.kurt() + 3, "days": len(r),
    }
    if bench is not None:
        b = bench.reindex(r.index).fillna(0)
        out["beta"] = np.cov(r, b)[0, 1] / b.var() if b.var() > 0 else np.nan
        out["correlation"] = r.corr(b)
    return out


def deflated_sharpe(r: pd.Series, n_trials: int, trial_sharpes_sd: float) -> float:
    """Probability the true Sharpe exceeds the best of n_trials unskilled strategies.

    trial_sharpes_sd: cross-sectional std of the (per-period) Sharpe ratios of all variants
    tried. Inputs are per-period (daily) Sharpe ratios as in the original paper.
    """
    r = r.dropna()
    T = len(r)
    sr = r.mean() / r.std()
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    emc = 0.5772156649
    n = max(n_trials, 2)
    sr0 = trial_sharpes_sd * ((1 - emc) * stats.norm.ppf(1 - 1 / n)
                              + emc * stats.norm.ppf(1 - 1 / (n * np.e)))
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return float(stats.norm.cdf(z))


def drawdown(r: pd.Series) -> pd.Series:
    eq = (1 + r.fillna(0)).cumprod()
    return eq / eq.cummax() - 1
