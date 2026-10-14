"""Data-quality checks run before any research.

Each check returns a tidy frame of flagged observations so the audit notebook can show
exactly what was found and what was done about it.
"""

from __future__ import annotations

import pandas as pd


def extreme_moves(total_return: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """Single-day total returns beyond +/- threshold (typical sign of a bad split adjustment)."""
    s = total_return.stack()
    s = s[s.abs() > threshold]
    out = s.rename("return").reset_index()
    out.columns = ["date", "id", "return"]
    return out.sort_values("date")


def reversal_pairs(total_return: pd.DataFrame, threshold: float = 0.4) -> pd.DataFrame:
    """Large move followed next day by an offsetting move: a bad print, not a real event."""
    r = total_return
    nxt = r.shift(-1)
    mask = (r.abs() > threshold) & (nxt.abs() > threshold) & (r * nxt < 0)
    s = r[mask].stack()
    out = s.rename("return").reset_index()
    out.columns = ["date", "id", "return"]
    out["next_return"] = [nxt.at[d, i] for d, i in zip(out["date"], out["id"])]
    return out


def stale_runs(total_return: pd.DataFrame, min_days: int = 10) -> pd.DataFrame:
    """Runs of >= min_days consecutive zero returns while the name is in the universe."""
    rows = []
    for col in total_return.columns:
        r = total_return[col].dropna()
        z = (r == 0).astype(int)
        grp = (z != z.shift()).cumsum()
        for _, block in r[z == 1].groupby(grp[z == 1]):
            if len(block) >= min_days:
                rows.append({"id": col, "start": block.index[0], "end": block.index[-1],
                             "days": len(block)})
    return pd.DataFrame(rows, columns=["id", "start", "end", "days"])


def coverage(total_return: pd.DataFrame, member: pd.DataFrame) -> pd.DataFrame:
    """Share of in-universe trading days with a valid return, per name."""
    have = total_return.notna() & member
    expected = member.sum()
    got = have.sum()
    out = pd.DataFrame({"expected_days": expected, "days_with_data": got})
    out["coverage"] = (got / expected.replace(0, pd.NA)).astype(float)
    return out.sort_values("coverage")
