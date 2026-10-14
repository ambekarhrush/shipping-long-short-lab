"""Point-in-time investability screens. Only information available on day t is used."""

from __future__ import annotations

import pandas as pd

MIN_ADV_USD = 1_000_000   # 60-day median traded value
MIN_PRICE_USD = 2.0
ADV_WINDOW = 60


def median_adv(dollar_volume: pd.DataFrame, window: int = ADV_WINDOW) -> pd.DataFrame:
    return dollar_volume.rolling(window, min_periods=window // 2).median()


def investable(panel, min_adv: float = MIN_ADV_USD, min_price: float = MIN_PRICE_USD,
               frozen: pd.DataFrame | None = None) -> pd.DataFrame:
    """True where a name is in its segment window, liquid enough, above the price floor
    and not trading on takeover terms. Evaluated on t-1 data to avoid look-ahead."""
    adv = median_adv(panel.dollar_volume).shift(1)
    px = panel.price_usd.ffill(limit=5).shift(1)
    ok = (adv >= min_adv) & (px >= min_price) & panel.total_return.notna()
    if frozen is not None:
        ok &= ~frozen.reindex_like(ok).fillna(False).astype(bool)
    return ok
