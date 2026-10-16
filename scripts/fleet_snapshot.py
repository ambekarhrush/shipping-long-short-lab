"""Take a live position snapshot of the listed fleets for the FleetWatch map.

Listens to aisstream.io for a few minutes and keeps the latest position of every ship whose
broadcast name matches a vessel in data/reference/fleet_register.csv. Static reports
(ship type, IMO, draught, destination) are merged in when they arrive, and a ship is kept only
when its broadcast type is cargo/tanker (70-89) or unknown, so name collisions with tugs or
fishing boats are dropped. Repeated runs merge into data/fleet/snapshot.csv (newest wins).

    python scripts/fleet_snapshot.py --seconds 170
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fleet" / "snapshot.csv"


def norm(name: str) -> str:
    s = re.sub(r"\(.*?\)", "", str(name).upper())
    s = re.sub(r"[^A-Z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


async def listen(seconds: float, key: str, names: set[str]) -> tuple[dict, dict]:
    import websockets

    pos, static = {}, {}
    sub = {"APIKey": key, "BoundingBoxes": [[[-90, -180], [90, 180]]],
           "FilterMessageTypes": ["ShipStaticData", "PositionReport"]}
    end = time.monotonic() + seconds
    async with websockets.connect("wss://stream.aisstream.io/v0/stream", max_size=2**22) as ws:
        await ws.send(json.dumps(sub))
        while time.monotonic() < end:
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
            except asyncio.TimeoutError:
                continue
            meta, kind = m.get("MetaData", {}), m.get("MessageType")
            nm = norm(meta.get("ShipName", ""))
            if nm not in names:
                continue
            body = m.get("Message", {}).get(kind, {})
            mmsi = meta.get("MMSI")
            if kind == "PositionReport":
                pos[mmsi] = dict(mmsi=mmsi, vessel_key=nm, lat=meta.get("latitude"), lon=meta.get("longitude"),
                                 sog=body.get("Sog"), cog=body.get("Cog"), heading=body.get("TrueHeading"),
                                 nav_status=body.get("NavigationalStatus"), time_utc=str(meta.get("time_utc"))[:19])
            elif kind == "ShipStaticData":
                static[mmsi] = dict(mmsi=mmsi, ship_type=body.get("Type"), imo=body.get("ImoNumber"),
                                    draught=body.get("MaximumStaticDraught"), destination=str(body.get("Destination", "")).strip())
    return pos, static


def main(seconds: float) -> None:
    load_dotenv(ROOT / ".env")
    reg = pd.read_csv(ROOT / "data/reference/fleet_register.csv")
    pos, static = asyncio.run(listen(seconds, os.environ["AISSTREAM_API_KEY"], set(reg.vessel_key)))
    new = pd.DataFrame(pos.values())
    if new.empty:
        print("no fleet positions this run")
        return
    st = pd.DataFrame(static.values()) if static else pd.DataFrame(columns=["mmsi"])
    new = new.merge(st, on="mmsi", how="left")
    if OUT.exists():
        old = pd.read_csv(OUT)
        for c in ("ship_type", "imo", "draught", "destination"):  # keep static fields seen in earlier runs
            if c in old:
                fill = old.set_index("mmsi")[c]
                new[c] = new[c].fillna(new.mmsi.map(fill)) if c in new else new.mmsi.map(fill)
        new = pd.concat([old, new]).sort_values("time_utc").drop_duplicates("mmsi", keep="last")
    new.to_csv(OUT, index=False)
    print(f"{len(pos)} positions this run; {len(new)} ships in snapshot")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=170)
    main(ap.parse_args().seconds)
