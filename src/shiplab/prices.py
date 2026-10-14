"""Price download and caching (Yahoo Finance and Tiingo).

Raw vendor responses are cached under ``data/cache`` (git-ignored). Each cached frame
has columns ``close``, ``adj_close`` (vendor's split and dividend adjusted series, kept
for reference only), ``volume``, ``dividend`` and ``split`` (the split ratio effective
that day, 1.0 otherwise), in the listing currency.

Total returns are NOT taken from the vendor's adjusted close: vendors miss liquidating
and special distributions. ``total_return`` rebuilds them from prices, cash distributions
and split ratios.
"""

from __future__ import annotations

import os
import time
import warnings

import pandas as pd
import requests
from dotenv import load_dotenv

from .config import CACHE, ROOT, WARMUP_START

load_dotenv(ROOT / ".env")
PRICE_CACHE = CACHE / "prices"


def _cache_path(source: str, symbol: str):
    return PRICE_CACHE / f"{source}__{symbol.replace('/', '_')}.parquet"


def fetch_yahoo(symbol: str) -> pd.DataFrame:
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        h = yf.Ticker(symbol).history(start=WARMUP_START, auto_adjust=False, actions=True)
    if h.empty:
        raise ValueError(f"Yahoo returned no data for {symbol}")
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    return pd.DataFrame(
        {
            "close": h["Close"],
            "adj_close": h["Adj Close"],
            "volume": h["Volume"].astype(float),
            "dividend": h["Dividends"].astype(float),
            # Yahoo's unadjusted-mode Close is already split-adjusted
            "split": 1.0,
            "close_is_split_adjusted": True,
        }
    )


def fetch_tiingo(symbol: str) -> pd.DataFrame:
    key = os.environ.get("TIINGO_API_KEY")
    if not key:
        raise RuntimeError("TIINGO_API_KEY missing: add it to .env in the project root")
    url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices"
    r = requests.get(
        url,
        params={"startDate": WARMUP_START, "token": key, "format": "json"},
        timeout=60,
    )
    r.raise_for_status()
    js = r.json()
    if not js:
        raise ValueError(f"Tiingo returned no data for {symbol}")
    d = pd.DataFrame(js)
    d.index = pd.to_datetime(d["date"]).dt.tz_localize(None).dt.normalize()
    return pd.DataFrame(
        {
            "close": d["close"],
            "adj_close": d["adjClose"],
            "volume": d["volume"].astype(float),
            "dividend": d["divCash"].astype(float),
            "split": d["splitFactor"].astype(float).replace(0, 1.0),
            "close_is_split_adjusted": False,
        }
    )


FETCHERS = {"yahoo": fetch_yahoo, "tiingo": fetch_tiingo}


def load(source: str, symbol: str, refresh: bool = False, pause: float = 0.4) -> pd.DataFrame:
    path = _cache_path(source, symbol)
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    PRICE_CACHE.mkdir(parents=True, exist_ok=True)
    df = FETCHERS[source](symbol)
    df.to_parquet(path)
    time.sleep(pause)
    return df


def fred(series_id: str, refresh: bool = False) -> pd.Series:
    """A FRED series via the public CSV endpoint (no key needed)."""
    path = CACHE / "fred" / f"{series_id}.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)[series_id]
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    d = pd.read_csv(url, na_values=["."])
    d.columns = ["date", series_id]
    d["date"] = pd.to_datetime(d["date"])
    d = d.set_index("date").dropna()
    d.to_parquet(path)
    return d[series_id]


def usd_per_nok(refresh: bool = False) -> pd.Series:
    """USD value of one NOK from the Federal Reserve H.10 noon rate (DEXNOUS = NOK per USD).

    Yahoo's NOK=X is not used: it contains bad prints (e.g. 7.74 on 2020-03-20 against an
    official 11.68), which would fabricate a 45% one-day move in every Oslo-listed stock.
    """
    return (1.0 / fred("DEXNOUS", refresh=refresh)).rename("usd_per_nok")


def total_return(df: pd.DataFrame) -> pd.Series:
    """Daily total return in listing currency: (P_t + D_t) / (P_{t-1} / split_t) - 1.

    Zero-volume days carry a stale quote, not a trade: their return is NaN and the next
    traded day is measured from the last traded price. Rows passed in must be sorted.
    """
    traded = df["volume"].fillna(0) > 0
    df = df[traded | (df["dividend"].fillna(0) > 0)]
    close, div = df["close"], df["dividend"].fillna(0.0)
    split = df["split"].fillna(1.0) if "split" in df else 1.0
    if "close_is_split_adjusted" in df and bool(df["close_is_split_adjusted"].iloc[0]):
        split = 1.0
    if not isinstance(split, float):
        split = split.reindex(close.index).fillna(1.0)
    prev = close.shift(1) / split
    return (close + div) / prev - 1.0
