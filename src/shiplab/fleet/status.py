"""Daily ship states and company-level operating signals from AIS.

States per ship-day (last observation of the UTC day):
  underway   speed over ground >= 3 kn
  anchored   AIS nav status 1, or speed < 1 kn with no port within 5 nm  (waiting / idle)
  moored     AIS nav status 5, or speed < 1 kn within 5 nm of a port     (loading/discharging)
  drifting   1-3 kn, not otherwise classified
  dark       no message for the day (coverage gap or transponder off)

Laden vs ballast: the reported static draught relative to the deepest draught seen for that
ship so far (>= 75% -> laden). Each ship needs one observed loaded voyage before this is
reliable; until then it is 'unknown'. This is the main warm-up constraint of FleetWatch.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import DATA

REGIONS = [  # (name, lat_min, lat_max, lon_min, lon_max) - first match wins
    ("Arabian Gulf", 22, 31, 47, 57), ("Red Sea", 12, 30, 32, 44), ("Gulf of Aden", 10, 16, 43, 54),
    ("Med / Black Sea", 30, 47, -6, 42), ("NW Europe", 47, 66, -12, 30), ("US Gulf", 18, 31, -98, -80),
    ("US East Coast", 25, 46, -80, -60), ("Caribbean", 8, 25, -88, -58), ("Brazil", -35, 5, -55, -30),
    ("West Africa", -20, 15, -20, 15), ("South Africa / Cape", -40, -20, 10, 40),
    ("Indian Ocean", -40, 22, 40, 95), ("SE Asia", -12, 22, 95, 125), ("China / N Asia", 18, 45, 105, 145),
    ("Australia", -45, -10, 110, 160), ("North Pacific", 0, 66, 145, 180), ("North Pacific", 0, 66, -180, -110),
    ("South Pacific", -66, 0, 160, 180), ("South Pacific", -66, 0, -180, -70),
    ("North Atlantic", 0, 66, -60, -12), ("South Atlantic", -66, 0, -40, 20),
]


def region(lat: float, lon: float) -> str:
    for name, a, b, c, d in REGIONS:
        if a <= lat <= b and c <= lon <= d:
            return name
    return "Other"


def load_positions(raw_dir: Path = DATA / "fleet" / "raw") -> pd.DataFrame:
    rows = []
    for f in sorted(raw_dir.rglob("*_position.jsonl.gz")):
        with gzip.open(f, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                m, meta = r["msg"], r["meta"]
                rows.append({"rx": r["rx"], "mmsi": meta.get("MMSI"),
                             "lat": meta.get("latitude"), "lon": meta.get("longitude"),
                             "sog": m.get("Sog"), "nav": m.get("NavigationalStatus")})
    df = pd.DataFrame(rows)
    if len(df):
        df["rx"] = pd.to_datetime(df["rx"])
    return df


def haversine_nm(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 3440.065 * 2 * np.arcsin(np.sqrt(a))


def near_port(lat, lon, ports: pd.DataFrame, nm: float = 5.0) -> np.ndarray:
    if ports is None or not len(ports):
        return np.zeros(len(lat), dtype=bool)
    out = np.zeros(len(lat), dtype=bool)
    plat, plon = ports["lat"].to_numpy(), ports["lon"].to_numpy()
    for i, (a, b) in enumerate(zip(lat, lon)):
        box = (np.abs(plat - a) < 0.2) & (np.abs(plon - b) < 0.3)
        if box.any():
            out[i] = (haversine_nm(a, b, plat[box], plon[box]) <= nm).any()
    return out


def daily_states(pos: pd.DataFrame, static: pd.DataFrame, ports: pd.DataFrame | None = None):
    if not len(pos):
        return pd.DataFrame()
    pos = pos.dropna(subset=["lat", "lon"]).sort_values("rx").copy()
    pos["day"] = pos["rx"].dt.floor("D")
    last = pos.groupby(["mmsi", "day"]).last().reset_index()
    port = near_port(last["lat"].to_numpy(), last["lon"].to_numpy(), ports)
    sog = last["sog"].fillna(0).to_numpy()
    nav = last["nav"].to_numpy()
    state = np.where(sog >= 3, "underway",
             np.where((nav == 5) | ((sog < 1) & port), "moored",
             np.where((nav == 1) | (sog < 1), "anchored", "drifting")))
    last["state"] = state
    last["region"] = [region(a, b) for a, b in zip(last["lat"], last["lon"])]
    # draught: latest static report on or before the day, vs max seen so far
    if static is not None and len(static):
        st = static[["rx", "mmsi", "draught"]].dropna().copy()
        st["rx"] = pd.to_datetime(st["rx"])
        st = st.sort_values("rx")
        st["max_seen"] = st.groupby("mmsi")["draught"].cummax()
        st["day"] = st["rx"].dt.floor("D")
        st = st.groupby(["mmsi", "day"]).last().reset_index()
        last = pd.merge_asof(last.sort_values("day"), st[["day", "mmsi", "draught", "max_seen"]]
                             .sort_values("day"), on="day", by="mmsi", direction="backward")
        ratio = last["draught"] / last["max_seen"]
        last["laden"] = np.where(ratio.isna(), "unknown", np.where(ratio >= 0.75, "laden", "ballast"))
    else:
        last["laden"] = "unknown"
    return last[["mmsi", "day", "lat", "lon", "sog", "state", "region", "laden"]]


def company_signals(states: pd.DataFrame, identity: pd.DataFrame) -> pd.DataFrame:
    """Company x day: coverage, idle share, laden share, moving share, top region share."""
    if not len(states):
        return pd.DataFrame()
    m = states.merge(identity[["mmsi", "universe_id", "dwt"]], on="mmsi", how="inner")
    fleet = identity[identity["status"] == "matched"].groupby("universe_id")["dwt"].sum()
    g = m.groupby(["universe_id", "day"])
    out = pd.DataFrame({
        "ships_seen": g["mmsi"].nunique(),
        "dwt_seen": g["dwt"].sum(),
        "idle_share": g.apply(lambda d: d.loc[d.state == "anchored", "dwt"].sum() / d.dwt.sum()),
        "moving_share": g.apply(lambda d: d.loc[d.state == "underway", "dwt"].sum() / d.dwt.sum()),
        "laden_share": g.apply(lambda d: d.loc[d.laden == "laden", "dwt"].sum()
                               / max(d.loc[d.laden != "unknown", "dwt"].sum(), 1)),
    }).reset_index()
    out["coverage"] = out["dwt_seen"] / out["universe_id"].map(fleet)
    return out
