"""Historical (2015-2025) ship-level signals from NOAA US-waters AIS.

Pre-registered in docs/PREREGISTRATION_FLEET_HISTORY.md. Inputs:
  * data/reference/fleet_history.csv - fleet tables parsed from every annual report since 2014
    (id, period, filed, vessel, dwt, built)
  * data/cache/noaa/YYYYMMDD.parquet - one sampled Wednesday per week, ships >= 140 m, hourly

Attribution is point in time: on sample day d a ship counts for owner c only if it appears in
c's most recent fleet table filed before d (and no more than 550 days earlier). Names claimed by
two owners on the same day are dropped.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..config import CACHE, REFERENCE
from .identity import LENGTH_BAND, norm
from .status import near_port

TANKERS = {"FRO", "DHT", "NAT", "TNK", "INSW", "TEN", "PSHG", "STNG", "ASC", "TRMD", "HAFNI", "OET",
           "GNRT", "DSSI", "NNA", "EURN"}
ID_MAP = {"PSHG": "PSHG_T"}


def vessel_class(dwt, tanker):
    if tanker:
        return ("vlcc" if dwt >= 200000 else "suezmax" if dwt >= 120000 else "aframax_lr2" if dwt >= 80000
                else "lr1_panamax" if dwt >= 60000 else "mr" if dwt >= 40000 else "handy_tanker")
    return ("newcastlemax" if dwt >= 195000 else "capesize" if dwt >= 120000 else "post_panamax" if dwt >= 85000
            else "kamsarmax_panamax" if dwt >= 68000 else "ultramax_supramax" if dwt >= 48000 else "handysize")


def load_fleets() -> pd.DataFrame:
    f = pd.read_csv(REFERENCE / "fleet_history.csv")
    f["filed"] = pd.to_datetime(f["filed"])
    f["key"] = f["vessel"].map(norm).str.replace(r"^M[ /]?[VT] ", "", regex=True)
    f["tanker"] = f["id"].isin(TANKERS)
    f["vclass"] = [vessel_class(d, t) for d, t in zip(f["dwt"], f["tanker"])]
    return f


def fleet_on(fleets: pd.DataFrame, d: pd.Timestamp, max_age_days: int = 550) -> pd.DataFrame:
    known = fleets[(fleets["filed"] < d) & (fleets["filed"] >= d - pd.Timedelta(days=max_age_days))]
    latest = known.groupby("id")["filed"].transform("max")
    cur = known[known["filed"] == latest].drop_duplicates(["id", "key"])
    dup = cur["key"].duplicated(keep=False)
    return cur[~dup]


def ship_days(noaa_dir: Path = CACHE / "noaa", ports: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per (sample day, owner, ship): state flags, with point-in-time attribution."""
    fleets = load_fleets()
    ports = pd.read_csv(REFERENCE / "ports.csv") if ports is None else ports
    rows, max_draft = [], {}
    for p in sorted(noaa_dir.glob("*.parquet")):
        d = pd.Timestamp(p.stem)
        cur = fleet_on(fleets, d)
        if cur.empty:
            continue
        x = pd.read_parquet(p).sort_values("hour").groupby("MMSI").last().reset_index()
        x["key"] = x["VesselName"].map(norm)
        m = x.merge(cur[["id", "key", "vclass"]], on="key", how="inner")
        if m.empty:
            continue
        lo = m["vclass"].map(lambda c: LENGTH_BAND[c][0] - 15)
        hi = m["vclass"].map(lambda c: LENGTH_BAND[c][1] + 15)
        m = m[(m["Length"] >= lo) & (m["Length"] <= hi)].copy()
        port = near_port(m["LAT"].to_numpy(), m["LON"].to_numpy(), ports)
        m["idle"] = (m["SOG"].fillna(0) < 1) & ~port
        ident = m["IMO"].fillna(m["MMSI"].astype(str))
        laden = []
        for i, dr in zip(ident, m["Draft"]):
            if pd.notna(dr) and dr > 0:
                max_draft[i] = max(max_draft.get(i, 0), dr)
            mx = max_draft.get(i)
            laden.append(np.nan if (mx is None or pd.isna(dr) or dr <= 0) else float(dr >= 0.75 * mx))
        m["laden"] = laden
        m["date"] = d
        rows.append(m[["date", "id", "key", "MMSI", "IMO", "idle", "laden"]])
    out = pd.concat(rows, ignore_index=True)
    out["id"] = out["id"].replace(ID_MAP)
    return out


def monthly_signals(sd: pd.DataFrame, window: int = 8, min_obs: int = 3) -> pd.DataFrame:
    """Company x month-end: idle share and laden share over the trailing `window` samples."""
    g = sd.groupby(["date", "id"]).agg(obs=("key", "size"), idle=("idle", "sum"),
                                       laden=("laden", "sum"), laden_n=("laden", "count")).reset_index()
    wide = {c: g.pivot(index="date", columns="id", values=c).fillna(0) for c in ("obs", "idle", "laden", "laden_n")}
    roll = {c: v.rolling(window, min_periods=window // 2).sum() for c, v in wide.items()}
    idle_share = (roll["idle"] / roll["obs"]).where(roll["obs"] >= min_obs)
    laden_share = (roll["laden"] / roll["laden_n"]).where(roll["laden_n"] >= min_obs)
    me = lambda f: f.resample("ME").last()  # noqa: E731
    return pd.concat({"idle_share": me(idle_share), "laden_share": me(laden_share),
                      "obs": me(roll["obs"])}, axis=1)
