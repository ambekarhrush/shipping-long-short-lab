"""Link register vessels to AIS identities (MMSI, IMO) using static reports.

Matching rule, in order of confidence:
  1. exact normalised name match AND AIS ship type consistent with the segment
     (tanker 80-89 / cargo 70-79) AND hull length consistent with the vessel class;
  2. if several AIS identities share the name, the one whose length best fits the
     register DWT (via a class length band) wins; ties stay 'ambiguous'.
Unmatched and ambiguous vessels are listed, never silently guessed.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import pandas as pd

from ..config import DATA, REFERENCE

# Typical length overall (m) by class; generous bands
LENGTH_BAND = {
    "newcastlemax": (285, 310), "capesize": (270, 300), "post_panamax": (225, 260),
    "kamsarmax_panamax": (215, 235), "ultramax_supramax": (180, 205), "handysize": (150, 190),
    "vlcc": (310, 345), "suezmax": (265, 285), "aframax_lr2": (235, 255),
    "lr1_panamax": (215, 235), "mr": (170, 195), "handy_tanker": (140, 185),
}


def norm(name: str) -> str:
    s = re.sub(r"\(.*?\)", "", str(name).upper())
    s = re.sub(r"[^A-Z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def load_static(raw_dir: Path = DATA / "fleet" / "raw") -> pd.DataFrame:
    rows = []
    for f in sorted(raw_dir.rglob("*_static.jsonl.gz")):
        with gzip.open(f, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                m, meta = r["msg"], r["meta"]
                dim = m.get("Dimension") or {}
                rows.append({
                    "rx": r["rx"], "mmsi": meta.get("MMSI"), "imo": m.get("ImoNumber"),
                    "ais_name": norm(m.get("Name", "")), "ais_type": m.get("Type"),
                    "length": (dim.get("A") or 0) + (dim.get("B") or 0),
                    "draught": m.get("MaximumStaticDraught"), "destination": m.get("Destination"),
                })
    return pd.DataFrame(rows)


def build(static: pd.DataFrame | None = None) -> pd.DataFrame:
    reg = pd.read_csv(REFERENCE / "fleet_register.csv")
    reg = reg[~reg["newbuild"]].copy()
    static = load_static() if static is None else static
    ids = (static.sort_values("rx").groupby("mmsi").last().reset_index()
           if len(static) else pd.DataFrame(columns=["mmsi", "imo", "ais_name", "ais_type", "length"]))
    out = []
    for r in reg.itertuples():
        cand = ids[ids["ais_name"] == r.vessel_key]
        want = range(80, 90) if r.segment == "tankers" else range(70, 80)
        cand = cand[cand["ais_type"].isin(list(want))]
        lo, hi = LENGTH_BAND.get(r.vessel_class, (0, 999))
        fit = cand[(cand["length"] >= lo - 10) & (cand["length"] <= hi + 10)]
        if len(fit) == 1:
            c, status = fit.iloc[0], "matched"
        elif len(fit) > 1:
            c, status = fit.iloc[0], "ambiguous"
        elif len(cand) == 1:
            c, status = cand.iloc[0], "matched_name_type_only"
        else:
            c, status = None, "unmatched"
        out.append({
            "universe_id": r.universe_id, "vessel": r.vessel, "vessel_key": r.vessel_key,
            "vessel_class": r.vessel_class, "dwt": r.dwt, "status": status,
            "mmsi": None if c is None else int(c["mmsi"]),
            "imo": None if c is None else c["imo"],
            "ais_length": None if c is None else c["length"],
        })
    df = pd.DataFrame(out)
    df.loc[df["status"] == "matched_name_type_only", "status"] = "matched"
    (DATA / "fleet").mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA / "fleet" / "identity.csv", index=False)
    return df
