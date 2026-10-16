"""Baltic Exchange freight indices (daily, via Barchart) and the freight ETFs.

Index families:
  BDI  Baltic Dry Index (composite);  BCI capesize, BPI panamax, BSI supramax, BHSI handysize
  BDTI Baltic Dirty Tanker Index (crude);  BCTI Baltic Clean Tanker Index (products)
  BLPG Baltic VLGC (LPG, from 2019);  BLNG Baltic LNG (sparse, from 2019)

Source file: data/manual/baltic_indices_barchart_*.csv (symbol,date,close), downloaded from
Barchart's public price-history pages. The raw file is not redistributed in the repo.
"""

from __future__ import annotations

import pandas as pd

from .config import DATA

MANUAL = DATA / "manual"

SEGMENT_FREIGHT = {          # the freight index each segment's earnings track most closely
    "dry_bulk": "BDI",
    "tankers": "BDTI",
    "gas": "BLPG",
    "containers": None,      # no free container charter index; equity-implied factor used
}


def load() -> pd.DataFrame:
    files = sorted(MANUAL.glob("baltic_indices_barchart_*.csv"))
    if not files:
        raise FileNotFoundError("Place baltic_indices_barchart_*.csv in data/manual/")
    d = pd.read_csv(files[-1])
    d["symbol"] = d["symbol"].str.replace(".BI", "", regex=False)
    d["date"] = pd.to_datetime(d["date"])
    wide = d.pivot_table(index="date", columns="symbol", values="close", aggfunc="last")
    return wide.sort_index()


def log_change(wide: pd.DataFrame, days: int) -> pd.DataFrame:
    import numpy as np

    return np.log(wide).diff(days)
