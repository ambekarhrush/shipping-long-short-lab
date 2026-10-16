"""Stock-level signals. Every signal at date t uses information available at the close of t.

value        book-to-market: equity / (as-traded price x shares), point-in-time
strength     balance-sheet strength: equity / total assets, point-in-time
freight_mom  operating-leverage momentum: (stock's freight beta) x (segment freight momentum).
             When freight is rising the high-beta names should lead, and vice versa.
residual     equity-vs-freight dislocation: 20-day cumulative residual of the stock against
             its rolling freight + market model, as a z-score (sleeve 3 trades it back)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import freight, fundamentals, prices
from .universe import tradable


def as_traded_price_usd(panel) -> pd.DataFrame:
    reg = tradable().set_index("id")
    usd_nok = prices.usd_per_nok()
    out = {}
    for i, df in panel.raw.items():
        df = df[~df.index.duplicated(keep="last")].sort_index()
        px = prices.as_traded_close(df)
        if reg.at[i, "currency"] == "NOK":
            px = px * usd_nok.reindex(px.index).ffill()
        out[i] = px.reindex(panel.total_return.index).ffill(limit=5)
    return pd.DataFrame(out).reindex(columns=panel.total_return.columns)


def value_and_strength(panel) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    idx, ids = panel.total_return.index, list(panel.total_return.columns)
    # fundamentals are filed under the SEC filer id; map universe ids that differ
    alias = {"PSHG_T": "PSHG", "PSHG_C": "PSHG"}
    fids = [alias.get(i, i) for i in ids]
    eq = fundamentals.as_of_panel("equity", idx, sorted(set(fids)))
    sh = fundamentals.as_of_panel("shares", idx, sorted(set(fids)))
    at = fundamentals.as_of_panel("assets", idx, sorted(set(fids)))
    eq = pd.DataFrame({i: eq[alias.get(i, i)] for i in ids})
    sh = pd.DataFrame({i: sh[alias.get(i, i)] for i in ids})
    at = pd.DataFrame({i: at[alias.get(i, i)] for i in ids})
    px = as_traded_price_usd(panel)
    mcap = px * sh
    btm = (eq / mcap).where((eq > 0) & (mcap > 0))
    strength = (eq / at).where(at > 0)
    return btm, strength, mcap


def _freight_for(segment: str, fr: pd.DataFrame, seg_basket: pd.Series) -> pd.Series:
    sym = freight.SEGMENT_FREIGHT.get(segment)
    if sym and sym in fr:
        return np.log(fr[sym]).diff()
    return np.log1p(seg_basket)   # containers / gaps: equity-implied segment factor


def segment_baskets(tr: pd.DataFrame, seg: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({s: tr[[c for c in tr.columns if seg.get(c) == s]].mean(axis=1)
                         for s in seg.unique()})


def freight_model(panel, fr: pd.DataFrame, market: pd.Series, window: int = 252):
    """Rolling OLS of daily stock returns on segment freight change and market return.

    Returns (beta_freight, residual) frames. Betas use data up to t only.
    """
    tr = panel.total_return
    seg = tradable().set_index("id")["segment"]
    baskets = segment_baskets(tr, seg)
    fr = fr.reindex(tr.index).ffill(limit=3)
    betas, resid = {}, {}
    for c in tr.columns:
        y = tr[c]
        f = _freight_for(seg[c], fr, baskets[seg[c]]).reindex(tr.index)
        m = market.reindex(tr.index)
        X = pd.concat([f, m], axis=1, keys=["f", "m"])
        ok = y.notna() & X.notna().all(axis=1)
        yy, ff, mm = y.where(ok), X["f"].where(ok), X["m"].where(ok)
        mean = lambda s: s.rolling(window, min_periods=window // 2).mean()  # noqa: E731
        cff = mean(ff * ff) - mean(ff) ** 2
        cmm = mean(mm * mm) - mean(mm) ** 2
        cfm = mean(ff * mm) - mean(ff) * mean(mm)
        cyf = mean(yy * ff) - mean(yy) * mean(ff)
        cym = mean(yy * mm) - mean(yy) * mean(mm)
        det = cff * cmm - cfm ** 2
        bf = (cyf * cmm - cym * cfm) / det
        bm = (cym * cff - cyf * cfm) / det
        a = mean(yy) - bf * mean(ff) - bm * mean(mm)
        # residual today uses yesterday's coefficients (no look-ahead)
        r = yy - (a.shift(1) + bf.shift(1) * ff + bm.shift(1) * mm)
        betas[c], resid[c] = bf, r
    return pd.DataFrame(betas), pd.DataFrame(resid)


def freight_momentum(fr: pd.DataFrame, tr: pd.DataFrame, lookback: int = 63) -> pd.DataFrame:
    """Segment freight momentum (log change over lookback) broadcast to each stock."""
    seg = tradable().set_index("id")["segment"]
    baskets = segment_baskets(tr, seg)
    fr = fr.reindex(tr.index).ffill(limit=3)
    out = {}
    for c in tr.columns:
        sym = freight.SEGMENT_FREIGHT.get(seg[c])
        if sym and sym in fr:
            out[c] = np.log(fr[sym]).diff(lookback)
        else:
            out[c] = np.log1p(baskets[seg[c]]).rolling(lookback).sum()
    return pd.DataFrame(out)


def residual_z(resid: pd.DataFrame, horizon: int = 20, norm_window: int = 252) -> pd.DataFrame:
    cum = resid.rolling(horizon, min_periods=horizon // 2).sum()
    sd = resid.rolling(norm_window, min_periods=norm_window // 2).std() * np.sqrt(horizon)
    return cum / sd


def zscore_within(sig: pd.DataFrame, mask: pd.DataFrame, groups: pd.Series) -> pd.DataFrame:
    """Cross-sectional rank-to-z within each group, among names where mask is True."""
    out = pd.DataFrame(np.nan, index=sig.index, columns=sig.columns)
    for g in groups.unique():
        cols = [c for c in sig.columns if groups.get(c) == g]
        s = sig[cols].where(mask[cols])
        r = s.rank(axis=1, pct=True)
        n = s.notna().sum(axis=1)
        z = (r - 0.5).mul(np.sqrt(12), axis=0)     # uniform ranks -> unit variance
        z.loc[n < 3] = np.nan
        out[cols] = z
    return out
