"""Assemble the daily USD total-return and liquidity panel for the universe."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import prices
from .universe import membership, tradable


@dataclass
class Panel:
    total_return: pd.DataFrame   # daily USD total return, NaN outside membership
    price_usd: pd.DataFrame      # unadjusted close in USD
    dollar_volume: pd.DataFrame  # USD traded value
    raw: dict                    # id -> vendor frame (listing currency)
    failures: dict               # id -> error message
    repairs: pd.DataFrame        # bad prints collapsed by repair_bad_prints


def build(refresh: bool = False, calendar: pd.DatetimeIndex | None = None) -> Panel:
    reg = tradable()
    raw, failures = {}, {}
    for row in reg.itertuples():
        try:
            raw[row.id] = prices.load(row.source, row.symbol, refresh=refresh)
        except Exception as exc:  # recorded and reported in the data audit
            failures[row.id] = f"{type(exc).__name__}: {exc}"

    if calendar is None:
        spy = prices.load("yahoo", "SPY", refresh=refresh)
        calendar = spy.index
    usd_nok = prices.usd_per_nok(refresh=refresh).reindex(calendar).ffill()

    tr, px, dv = {}, {}, {}
    ccy = reg.set_index("id")["currency"]
    for i, df in raw.items():
        df = df[~df.index.duplicated(keep="last")].sort_index()
        df = df[df.index.isin(calendar)]       # exchange holidays off the US calendar dropped
        r_local = prices.total_return(df)
        if ccy[i] == "NOK":
            fx = usd_nok.reindex(df.index)
            r = (1 + r_local) * (fx / fx.shift(1)) - 1
        else:
            fx = pd.Series(1.0, index=df.index)
            r = r_local
        tr[i] = r.reindex(calendar)
        px[i] = (df["close"] * fx).reindex(calendar)
        dv[i] = (df["close"] * df["volume"] * fx).reindex(calendar)

    member = membership(calendar)
    total_return = pd.DataFrame(tr).reindex(columns=member.columns)
    total_return = total_return.where(member)
    # the first in-universe day is measured against a pre-listing / pre-window price
    first_day = total_return.notna().cumsum().eq(1)
    total_return = total_return.mask(first_day)
    total_return, repairs = repair_bad_prints(total_return)
    price_usd = pd.DataFrame(px).reindex(columns=member.columns).where(member)
    dollar_volume = pd.DataFrame(dv).reindex(columns=member.columns).where(member)
    total_return = total_return.replace([np.inf, -np.inf], np.nan)
    return Panel(total_return, price_usd, dollar_volume, raw, failures, repairs)


def repair_bad_prints(r: pd.DataFrame, move: float = 0.30, tol: float = 0.10):
    """Collapse one-day spikes that fully reverse the next day.

    Rule: if |r_t| > move, |r_t+1| > move, opposite signs, and the two-day compounded
    return is within +/- tol, the day-t price is treated as a bad print: r_t is set to 0
    and r_t+1 to the two-day compounded return. Every repair is logged.
    """
    r = r.copy()
    nxt = r.shift(-1)
    two_day = (1 + r) * (1 + nxt) - 1
    hit = (r.abs() > move) & (nxt.abs() > move) & (r * nxt < 0) & (two_day.abs() < tol)
    log = []
    for d, i in hit.stack()[lambda s: s].index:
        pos = r.index.get_loc(d)
        log.append({"date": d, "id": i, "return": r.iat[pos, r.columns.get_loc(i)],
                    "next_return": nxt.at[d, i], "two_day": two_day.at[d, i]})
        r.iat[pos + 1, r.columns.get_loc(i)] = two_day.at[d, i]
        r.iat[pos, r.columns.get_loc(i)] = 0.0
    return r, pd.DataFrame(log, columns=["date", "id", "return", "next_return", "two_day"])
