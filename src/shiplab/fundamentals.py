"""Point-in-time fundamentals from SEC XBRL (companyfacts).

Each value enters the panel the trading day AFTER its filing date, never at its period end.
Built by scripts/fleet_sources-style extraction into data/reference/fundamentals_pit.parquet
(id, item, end, filed, val). Oslo-only issuers (JIN, TWENTY, ODF, MPCC, AGAS and pre-2023
history of OET/HAFNI/BWLPG) have no XBRL and are left blank, which removes them from the
fundamental ranks rather than guessing.
"""

from __future__ import annotations

import pandas as pd

from .config import REFERENCE


def load() -> pd.DataFrame:
    return pd.read_parquet(REFERENCE / "fundamentals_pit.parquet")


def as_of_panel(item: str, index: pd.DatetimeIndex, ids: list[str], lag_days: int = 1,
                max_age_days: int = 550) -> pd.DataFrame:
    """Latest value of `item` known at each date (filed + lag <= date), expiring if stale."""
    f = load()
    f = f[f["item"] == item].copy()
    f["known"] = f["filed"] + pd.Timedelta(days=lag_days)
    out = pd.DataFrame(index=index, columns=ids, dtype=float)
    for i in ids:
        g = f[f["id"] == i].sort_values(["known", "end"])
        if g.empty:
            continue
        # if several periods become known on the same day, keep the latest period end
        g = g.groupby("known").last()
        s = g["val"].astype(float).reindex(index.union(g.index)).ffill().reindex(index)
        e = g["end"].reindex(index.union(g.index)).ffill().reindex(index)
        stale = (index.to_series() - pd.to_datetime(e)).dt.days > max_age_days
        out[i] = s.where(~stale.values)
    return out
