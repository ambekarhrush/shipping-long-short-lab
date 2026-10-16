"""The three strategy sleeves. Each returns target weights (dates x names), unit gross per
active segment book, decided with information up to the close of each rebalance date.

1. pairs     mean reversion between similar companies in the same segment
2. factor    segment-neutral long/short on value + balance-sheet strength + freight momentum
3. residual  fade stock moves that are out of line with the stock's freight sensitivity
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def _inv_vol(names, vol_row):
    v = vol_row.reindex(names).clip(lower=0.005)
    w = 1 / v
    return w / w.sum()


def rebalance_dates(index: pd.DatetimeIndex, freq: str = "W-WED") -> pd.DatetimeIndex:
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.resample(freq).last().dropna().values)


# ---------------------------------------------------------------- sleeve 2: factor ranks
@dataclass
class FactorParams:
    quantile: float = 1 / 3
    weights: tuple = (1.0, 1.0, 1.0)   # value, strength, freight momentum


def factor_sleeve(z_value, z_strength, z_fmom, investable, seg, vol, dates, p: FactorParams):
    comp = (p.weights[0] * z_value.fillna(0) + p.weights[1] * z_strength.fillna(0)
            + p.weights[2] * z_fmom.fillna(0))
    have = z_value.notna() | z_strength.notna() | z_fmom.notna()
    comp = comp.where(have & investable)
    W = pd.DataFrame(0.0, index=dates, columns=comp.columns)
    for d in dates:
        row = comp.loc[d]
        books = []
        for s in seg.unique():
            names = [c for c in row.index if seg.get(c) == s and pd.notna(row[c])]
            if len(names) < 4:
                continue
            r = row[names].sort_values()
            k = max(1, int(round(len(r) * p.quantile)))
            short, long = list(r.index[:k]), list(r.index[-k:])
            w = pd.Series(0.0, index=W.columns)
            w[long] = 0.5 * _inv_vol(long, vol.loc[d])
            w[short] = -0.5 * _inv_vol(short, vol.loc[d])
            books.append(w)
        if books:
            W.loc[d] = sum(books) / len(books)
    return W


# ---------------------------------------------------------------- sleeve 3: residual fade
@dataclass
class ResidualParams:
    entry: float = 1.0
    horizon: int = 20


def residual_sleeve(rz, investable, seg, vol, dates, p: ResidualParams):
    sig = (-rz).where(investable)
    W = pd.DataFrame(0.0, index=dates, columns=rz.columns)
    for d in dates:
        row = sig.loc[d]
        books = []
        for s in seg.unique():
            names = [c for c in row.index if seg.get(c) == s and pd.notna(row[c])]
            if len(names) < 4:
                continue
            r = row[names]
            r = r - r.mean()                       # segment-neutral: relative dislocation
            long = list(r[r > p.entry].index)
            short = list(r[r < -p.entry].index)
            if not long or not short:
                continue
            w = pd.Series(0.0, index=W.columns)
            w[long] = 0.5 * _inv_vol(long, vol.loc[d])
            w[short] = -0.5 * _inv_vol(short, vol.loc[d])
            books.append(w)
        if books:
            W.loc[d] = sum(books) / len(books)
    return W


# ---------------------------------------------------------------- sleeve 1: pairs
@dataclass
class PairsParams:
    formation: int = 252
    min_corr: float = 0.6
    max_pvalue: float = 0.10
    max_strength_gap: float = 0.15
    entry: float = 2.0
    exit: float = 0.5
    stop: float = 4.0
    max_hold: int = 30
    zwin: int = 60
    pairs_per_segment: int = 5


def select_pairs(logp, tr, investable, seg, strength, d, p: PairsParams):
    from statsmodels.tsa.stattools import adfuller

    loc = logp.index.get_loc(d)
    if loc < p.formation:
        return []
    win = slice(logp.index[loc - p.formation + 1], d)
    ok = [c for c in logp.columns if investable.at[d, c]
          and logp.loc[win, c].notna().mean() > 0.9]
    out = []
    for s in seg.unique():
        names = [c for c in ok if seg.get(c) == s]
        cands = []
        corr = tr.loc[win, names].corr()
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if corr.at[a, b] < p.min_corr:
                    continue
                sa, sb = strength.at[d, a], strength.at[d, b]
                if pd.notna(sa) and pd.notna(sb) and abs(sa - sb) > p.max_strength_gap:
                    continue
                y, x = logp.loc[win, a], logp.loc[win, b]
                m = y.notna() & x.notna()
                beta = np.polyfit(x[m], y[m], 1)[0]
                if not (0.3 < beta < 3):
                    continue
                spread = y[m] - beta * x[m]
                try:
                    pv = adfuller(spread, maxlag=5, autolag=None)[1]
                except Exception:
                    continue
                if pv <= p.max_pvalue:
                    cands.append((corr.at[a, b], a, b, beta))
        cands.sort(reverse=True)
        out += [(a, b, beta) for _, a, b, beta in cands[: p.pairs_per_segment]]
    return out


def pairs_sleeve(logp, tr, investable, seg, strength, index, p: PairsParams, reform="QS"):
    """Daily state machine. Pairs re-selected each quarter on the trailing formation window."""
    W = pd.DataFrame(0.0, index=index, columns=logp.columns)
    reforms = set(rebalance_dates(index, reform.replace("QS", "QE")))
    active, pairs = {}, []
    for t, d in enumerate(index):
        if d in reforms:
            pairs = select_pairs(logp, tr, investable, seg, strength, d, p)
            active = {k: v for k, v in active.items() if k in {(a, b) for a, b, _ in pairs}}
        w = pd.Series(0.0, index=W.columns)
        for a, b, beta in pairs:
            hist = (logp[a] - beta * logp[b]).iloc[max(0, t - p.zwin + 1): t + 1]
            if hist.notna().sum() < p.zwin // 2 or not (investable.at[d, a] and investable.at[d, b]):
                active.pop((a, b), None)
                continue
            z = (hist.iloc[-1] - hist.mean()) / hist.std()
            st = active.get((a, b))
            if st is None and abs(z) > p.entry and abs(z) < p.stop:
                active[(a, b)] = {"side": -np.sign(z), "age": 0}
            elif st is not None:
                st["age"] += 1
                if abs(z) < p.exit or abs(z) > p.stop or st["age"] > p.max_hold or np.sign(z) == st["side"]:
                    active.pop((a, b))
            st = active.get((a, b))
            if st is not None:
                w[a] += 0.5 * st["side"]
                w[b] -= 0.5 * st["side"]
        n = len(active)
        if n:
            W.loc[d] = w / n
    return W
