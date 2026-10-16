"""AIS collector for aisstream.io (free, terrestrial coverage, websocket).

Usage (also run hourly by .github/workflows/fleetwatch.yml)::

    python -m shiplab.fleet.ais --minutes 8

Two message types are kept:
  * ShipStaticData  - name, IMO, ship type, dimensions, draught, destination, ETA
  * PositionReport  - position, speed, course, navigational status

Static reports are kept for cargo/tanker vessels (types 70-89) whose name appears in the
fleet register (or whose MMSI is already linked), so the identity table can be built and
refreshed; position reports are kept only for MMSIs already linked to the register. Output: data/fleet/raw/YYYY/MM/DD/HHMM_<kind>.jsonl.gz (append-only).
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from ..config import DATA, ROOT

URL = "wss://stream.aisstream.io/v0/stream"
RAW = DATA / "fleet" / "raw"
CARGO_TANKER_TYPES = range(70, 90)


def register_names() -> set[str]:
    import pandas as pd

    from ..config import REFERENCE
    from .identity import norm

    reg = pd.read_csv(REFERENCE / "fleet_register.csv")
    return set(reg["vessel"].map(norm))


def linked_mmsis() -> set[int]:
    path = DATA / "fleet" / "identity.csv"
    if not path.exists():
        return set()
    import pandas as pd

    ids = pd.read_csv(path)
    return set(ids.loc[ids["status"] == "matched", "mmsi"].astype(int))


async def _collect(minutes: float, key: str, out_dir: Path) -> dict:
    import websockets

    from .identity import norm

    tracked = linked_mmsis()
    names = register_names()
    stamp = datetime.now(timezone.utc)
    sub = {
        "APIKey": key,
        "BoundingBoxes": [[[-90, -180], [90, 180]]],
        "FilterMessageTypes": ["ShipStaticData", "PositionReport"],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / stamp.strftime("%Y/%m/%d")
    base.mkdir(parents=True, exist_ok=True)
    f_static = gzip.open(base / f"{stamp:%H%M}_static.jsonl.gz", "at")
    f_pos = gzip.open(base / f"{stamp:%H%M}_position.jsonl.gz", "at")
    n = {"messages": 0, "static_kept": 0, "position_kept": 0, "tracked_mmsi": len(tracked)}
    deadline = time.monotonic() + minutes * 60
    async with websockets.connect(URL, max_size=2**22, ping_interval=20) as ws:
        await ws.send(json.dumps(sub))
        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=30)
            except asyncio.TimeoutError:
                continue
            n["messages"] += 1
            msg = json.loads(raw)
            kind = msg.get("MessageType")
            meta = msg.get("MetaData", {})
            rec = {"rx": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "meta": meta, "msg": msg.get("Message", {}).get(kind, {})}
            if (kind == "ShipStaticData" and rec["msg"].get("Type") in CARGO_TANKER_TYPES
                    and (norm(rec["msg"].get("Name", "")) in names or meta.get("MMSI") in tracked)):
                f_static.write(json.dumps(rec, separators=(",", ":")) + "\n")
                n["static_kept"] += 1
            elif kind == "PositionReport" and meta.get("MMSI") in tracked:
                f_pos.write(json.dumps(rec, separators=(",", ":")) + "\n")
                n["position_kept"] += 1
    f_static.close()
    f_pos.close()
    return n


def collect(minutes: float = 8.0) -> dict:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("AISSTREAM_API_KEY")
    if not key:
        raise RuntimeError("AISSTREAM_API_KEY missing (.env locally, repository secret in CI)")
    return asyncio.run(_collect(minutes, key, RAW))


def _log(status: str, detail: str) -> None:
    """Append one line per run to data/fleet/collector_log.csv so failures are visible in the repo."""
    import csv, datetime as dt
    path = ROOT / "data" / "fleet" / "collector_log.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["utc", "status", "detail"])
        w.writerow([dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), status, detail[:300]])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=8.0)
    try:
        stats = collect(ap.parse_args().minutes)
        _log("ok", json.dumps(stats))
        print(json.dumps(stats))
    except Exception as e:  # never fail the workflow: log it and let the commit step record it
        _log("error", f"{type(e).__name__}: {e}")
        print(f"collector error: {type(e).__name__}: {e}")
