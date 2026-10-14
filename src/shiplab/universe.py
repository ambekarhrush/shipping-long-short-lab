"""Point-in-time universe register.

Every company that was a candidate at any point in the study window is listed in
``data/reference/universe.csv`` with the dates it belongs to a segment, how it left
(merger, take-private, bankruptcy, reclassification) and when a takeover was first made
public. Names with no recoverable free price history are kept in the register with
``include = 0`` so the survivorship gap is documented rather than hidden.
"""

from __future__ import annotations

import pandas as pd

from .config import REFERENCE, SEGMENTS


def load_register() -> pd.DataFrame:
    reg = pd.read_csv(REFERENCE / "universe.csv", dtype={"symbol": str})
    for col in ("start", "end", "deal_announced"):
        reg[col] = pd.to_datetime(reg[col])
    reg["include"] = reg["include"].astype(bool)
    return reg


def tradable(reg: pd.DataFrame | None = None) -> pd.DataFrame:
    reg = load_register() if reg is None else reg
    return reg[reg["include"] & reg["segment"].isin(SEGMENTS)].copy()


def membership(index: pd.DatetimeIndex, reg: pd.DataFrame | None = None) -> pd.DataFrame:
    """Boolean (date x id) matrix: inside the register's segment window."""
    reg = tradable(reg)
    out = pd.DataFrame(False, index=index, columns=reg["id"])
    for row in reg.itertuples():
        end = row.end if pd.notna(row.end) else index[-1]
        out.loc[(index >= row.start) & (index <= end), row.id] = True
    return out


def deal_frozen(index: pd.DatetimeIndex, reg: pd.DataFrame | None = None) -> pd.DataFrame:
    """Boolean (date x id) matrix: True once a takeover/bid is public.

    From that date the share price trades on deal terms, not on fundamentals, so no new
    signals are taken.
    """
    reg = tradable(reg)
    out = pd.DataFrame(False, index=index, columns=reg["id"])
    for row in reg.itertuples():
        if pd.notna(row.deal_announced):
            out.loc[index >= row.deal_announced, row.id] = True
    return out
