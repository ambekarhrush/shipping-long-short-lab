"""Trading-cost and financing assumptions (deliberately conservative for small caps).

cost per trade (one way) = half-spread(ADV tier) + impact
    half-spread : 5 bp if ADV >= $50m, 10 bp >= $20m, 20 bp >= $5m, 35 bp >= $1m, 60 bp below
    impact      : 0.1 x daily vol x sqrt(trade notional / ADV)       (square-root law)
borrow on shorts (annual) : 0.5% GC if ADV >= $20m, 2% >= $5m, 6% >= $1m, 15% below
dividends on shorts       : paid automatically (total returns include distributions)
NOK names                 : unhedged; FX moves are in the USD returns
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HALF_SPREAD_TIERS = [(50e6, 5), (20e6, 10), (5e6, 20), (1e6, 35), (0, 60)]
BORROW_TIERS = [(20e6, 0.005), (5e6, 0.02), (1e6, 0.06), (0, 0.15)]


def _tier(adv: pd.DataFrame, tiers) -> pd.DataFrame:
    out = pd.DataFrame(tiers[-1][1], index=adv.index, columns=adv.columns, dtype=float)
    for thr, val in reversed(tiers[:-1]):
        out = out.mask(adv >= thr, val)
    return out


def half_spread_bp(adv: pd.DataFrame) -> pd.DataFrame:
    return _tier(adv.fillna(0), HALF_SPREAD_TIERS)


def borrow_rate(adv: pd.DataFrame) -> pd.DataFrame:
    return _tier(adv.fillna(0), BORROW_TIERS)


def trading_cost(trade_w: pd.DataFrame, adv: pd.DataFrame, vol: pd.DataFrame,
                 aum: float) -> pd.Series:
    """Daily cost as a fraction of NAV for weight changes trade_w."""
    notional = trade_w.abs() * aum
    part = (notional / adv.replace(0, np.nan)).clip(upper=1.0).fillna(1.0)
    impact = 0.1 * vol.fillna(0.05) * np.sqrt(part)
    hs = half_spread_bp(adv) / 1e4
    return (trade_w.abs() * (hs + impact)).sum(axis=1)


def borrow_cost(w: pd.DataFrame, adv: pd.DataFrame) -> pd.Series:
    shorts = (-w).clip(lower=0)
    return (shorts * borrow_rate(adv) / 252).sum(axis=1)
