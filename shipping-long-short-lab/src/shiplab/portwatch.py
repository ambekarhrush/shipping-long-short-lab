"""IMF PortWatch: daily port calls, trade volumes and chokepoint transits (2019 onward).

PortWatch is built by the IMF and Oxford from satellite AIS. It is free, public and
backtestable, but aggregated by vessel type rather than by ship or owner. It feeds the
segment-level activity signals; ship-level work lives in ``shiplab.fleet``.

Source: https://portwatch.imf.org (ArcGIS feature services, no key required).
"""

from __future__ import annotations

import json
import time

import pandas as pd
import requests

from .config import CACHE

BASE = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
PW_CACHE = CACHE / "portwatch"

# Countries whose seaborne flows drive the four segments
KEY_COUNTRIES = [
    "AUS", "BRA", "GIN", "IDN", "ZAF", "CAN", "UKR",           # dry bulk exporters
    "CHN", "JPN", "KOR", "IND", "TWN", "VNM", "DEU", "NLD",    # importers / hubs
    "SAU", "ARE", "IRQ", "KWT", "QAT", "IRN", "RUS", "USA",    # oil/gas exporters
    "NOR", "NGA", "AGO", "MYS", "SGP", "GBR", "EGY", "MEX",
]


def _query(layer: str, params: dict, page: int = 1000) -> pd.DataFrame:
    url = f"{BASE}/{layer}/FeatureServer/0/query"
    rows, offset = [], 0
    while True:
        p = {"f": "json", "returnGeometry": "false", "resultOffset": offset,
             "resultRecordCount": page, **params}
        for attempt in range(4):
            try:
                r = requests.get(url, params=p, timeout=120)
                r.raise_for_status()
                js = r.json()
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(3 * (attempt + 1))
        feats = js.get("features", [])
        rows += [f["attributes"] for f in feats]
        if not js.get("exceededTransferLimit") and len(feats) < page:
            break
        offset += len(feats)
    return pd.DataFrame(rows)


def chokepoints(refresh: bool = False) -> pd.DataFrame:
    """Daily transits (count and capacity in tonnes) by vessel type at 28 chokepoints."""
    path = PW_CACHE / "chokepoints.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    PW_CACHE.mkdir(parents=True, exist_ok=True)
    d = _query("Daily_Chokepoints_Data", {"where": "1=1", "outFields": "*",
                                         "orderByFields": "ObjectId"})
    d["date"] = pd.to_datetime(d["date"])
    d = d.drop(columns=["ObjectId", "year", "month", "day"]).rename(
        columns={"portname": "chokepoint"})
    d.to_parquet(path)
    return d


def country_flows(refresh: bool = False, budget_s: float | None = None) -> pd.DataFrame:
    """Daily port calls and import/export tonnes by vessel type, summed by country."""
    path = PW_CACHE / "country_flows.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    PW_CACHE.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    fields = [f"{k}_{t}" for k in ("portcalls", "import", "export")
              for t in ("container", "dry_bulk", "tanker", "cargo")]
    stats = [{"statisticType": "sum", "onStatisticField": f, "outStatisticFieldName": f}
             for f in fields]
    frames = []
    for iso in KEY_COUNTRIES:  # one grouped query per country; each cached (resumable)
        part = PW_CACHE / "by_country" / f"{iso}.parquet"
        if part.exists() and not refresh:
            frames.append(pd.read_parquet(part))
            continue
        if budget_s is not None and time.time() - t0 > budget_s:
            raise TimeoutError("time budget reached; call again to resume")
        d = _query("Daily_Ports_Data", {
            "where": f"ISO3='{iso}'",
            "outStatistics": json.dumps(stats),
            "groupByFieldsForStatistics": "date",
            "orderByFields": "date",
        }, page=2000)
        d["ISO3"] = iso
        part.parent.mkdir(parents=True, exist_ok=True)
        d.to_parquet(part)
        frames.append(d)
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out.to_parquet(path)
    return out
