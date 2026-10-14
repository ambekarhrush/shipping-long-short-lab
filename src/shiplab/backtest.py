"""Portfolio simulation: sleeves -> risk-scaled, capped, beta-hedged, costed daily P&L.

Timing: targets decided at the close of day t are traded at the close of t+1 (one full day of
implementation lag) and earn returns from t+2. Weights drift with prices between trades.

Risk: each sleeve is scaled to an ex-ante volatility target estimated from the trailing
63 days of returns at current weights; sleeves are summed; per-name, gross and
liquidity caps are applied; residual market beta is hedged with SPY; a drawdown brake
halves exposure after a 15% strategy drawdown until it recovers to -7.5%.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import costs


@dataclass
class RiskParams:
    sleeve_vol: float = 0.06
    name_cap: float = 0.075
    gross_cap: float = 2.5
    adv_participation: float = 0.10
    aum: float = 50e6
    dd_brake: float = -0.15
    dd_release: float = -0.075
    hedge_beta: bool = True
    vol_window: int = 63


@dataclass
class Result:
    returns: pd.Series                 # net daily return
    gross_returns: pd.Series           # before costs
    weights: pd.DataFrame              # held weights (stocks)
    hedge: pd.Series                   # SPY weight
    costs: pd.DataFrame                # trading, borrow, hedge
    sleeve_returns: pd.DataFrame       # per sleeve, net of its own costs (approx.)
    attribution: dict = field(default_factory=dict)


def _expand(targets: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    return targets.reindex(index).ffill().fillna(0.0)


def vol_scale(targets: pd.DataFrame, tr: pd.DataFrame, target_vol: float, window: int) -> pd.DataFrame:
    """Scale each rebalance's book so its trailing-window volatility equals target_vol."""
    out = targets.copy()
    r = tr.fillna(0.0)
    for d in targets.index:
        w = targets.loc[d]
        if not w.abs().sum():
            continue
        loc = r.index.get_loc(d)
        hist = r.iloc[max(0, loc - window + 1): loc + 1]
        v = (hist @ w).std() * np.sqrt(252)
        out.loc[d] = w * (target_vol / v if v > 1e-6 else 0.0)
    return out


def run(sleeve_targets: dict[str, pd.DataFrame], tr: pd.DataFrame, investable: pd.DataFrame,
        adv: pd.DataFrame, vol: pd.DataFrame, beta_mkt: pd.DataFrame, spy: pd.Series,
        rp: RiskParams = RiskParams(), start=None, end=None) -> Result:
    idx = tr.loc[start:end].index
    trf = tr.reindex(idx).fillna(0.0)
    scaled = {}
    for name, T in sleeve_targets.items():
        T = T.loc[start:end]
        T = T.where(investable.reindex(T.index).fillna(False), 0.0)
        scaled[name] = _expand(vol_scale(T, tr, rp.sleeve_vol, rp.vol_window), idx)
    target = sum(scaled.values())

    # caps: per name, liquidity, gross
    liq_cap = (rp.adv_participation * adv.reindex(idx) / rp.aum).fillna(0.0)
    cap = np.minimum(rp.name_cap, liq_cap)
    target = target.clip(lower=-cap, upper=cap)
    g = target.abs().sum(axis=1)
    target = target.mul(np.minimum(1.0, rp.gross_cap / g.replace(0, np.nan)).fillna(0), axis=0)

    # one-day implementation lag
    target = target.shift(1).fillna(0.0)

    held = pd.DataFrame(0.0, index=idx, columns=tr.columns)
    w = pd.Series(0.0, index=tr.columns)
    hedge = pd.Series(0.0, index=idx)
    gross_r = pd.Series(0.0, index=idx)
    trade_cost = pd.Series(0.0, index=idx)
    brake, peak, eq = 1.0, 1.0, 1.0
    rebal_days = set(pd.concat(sleeve_targets.values()).index) if sleeve_targets else set()
    rebal_days = {idx[min(idx.get_loc(d) + 1, len(idx) - 1)] for d in rebal_days if d in idx}
    spy_r = spy.reindex(idx).fillna(0.0)
    bm = beta_mkt.reindex(idx).ffill().fillna(1.0)
    h = 0.0
    for t, d in enumerate(idx):
        new_w = w
        if d in rebal_days or t == 0:
            new_w = target.loc[d] * brake
            if rp.hedge_beta:
                h_new = -(new_w * bm.loc[d]).sum()
            else:
                h_new = 0.0
            dw = (new_w - w)
            trade_cost.loc[d] = costs.trading_cost(dw.to_frame().T, adv.loc[[d]].reindex(columns=dw.index),
                                                   vol.loc[[d]].reindex(columns=dw.index), rp.aum).iloc[0]
            trade_cost.loc[d] += abs(h_new - h) * 0.0001
            h = h_new
        w = new_w
        held.loc[d] = w
        hedge.loc[d] = h
        rp_ = float((w * trf.loc[d]).sum() + h * spy_r.loc[d])
        gross_r.loc[d] = rp_
        # drift
        growth = 1 + rp_
        w = w * (1 + trf.loc[d]) / growth if growth > 0 else w * 0
        h = h * (1 + spy_r.loc[d]) / growth if growth > 0 else 0.0
        eq *= growth
        peak = max(peak, eq)
        ddv = eq / peak - 1
        if brake == 1.0 and ddv < rp.dd_brake:
            brake = 0.5
        elif brake < 1.0 and ddv > rp.dd_release:
            brake = 1.0
    borrow = costs.borrow_cost(held, adv.reindex(idx))
    net = gross_r - trade_cost - borrow
    cost_df = pd.DataFrame({"trading": trade_cost, "borrow": borrow})

    # sleeve returns (approximate: each scaled sleeve alone, lagged, with proportional costs)
    sr = {}
    tot_abs = sum(s.abs() for s in scaled.values()).replace(0, np.nan)
    for name, S in scaled.items():
        s_lag = S.shift(1).fillna(0.0)
        share = (S.abs() / tot_abs).shift(1).fillna(0.0)
        sr[name] = (s_lag * trf).sum(axis=1) - (share.mean(axis=1).fillna(0) * (trade_cost + borrow))
    sleeve_returns = pd.DataFrame(sr)

    attrib = {
        "long": (held.clip(lower=0) * trf).sum(axis=1),
        "short": (held.clip(upper=0) * trf).sum(axis=1),
        "hedge": hedge * spy_r,
    }
    return Result(net, gross_r, held, hedge, cost_df, sleeve_returns, attrib)
