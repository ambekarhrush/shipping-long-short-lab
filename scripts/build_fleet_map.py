"""Build the FleetWatch map: docs/fleetwatch/index.html (GitHub Pages) plus Google-ready exports.

Inputs:  data/fleet/snapshot.csv (scripts/fleet_snapshot.py), data/reference/fleet_register.csv,
         data/reference/ports.csv, data/reference/universe.csv
Outputs: docs/fleetwatch/index.html   self-contained interactive map
         docs/fleetwatch/fleet.geojson
         docs/fleetwatch/fleetwatch.kml  import into Google My Maps or Google Earth

Ship state on the snapshot: "in port" within 5 nm of a PortWatch port and below 1 kn; "idle"
below 1 kn elsewhere (anchorage or drifting); otherwise "underway".
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "fleetwatch"
TEMPLATE = ROOT / "scripts" / "fleet_map_template.html"
WORLD = ROOT / "data" / "reference" / "world_countries_50m.json"
SEG = {"dry_bulk": "Dry bulk", "tankers": "Tankers", "containers": "Containers", "gas": "Gas"}


def nearest_port(lat, lon, ports):
    la, lo = np.radians(ports.lat.values), np.radians(ports.lon.values)
    a, b = np.radians(lat), np.radians(lon)
    d = 2 * 3440.065 * np.arcsin(np.sqrt(np.sin((la - a) / 2) ** 2 + np.cos(a) * np.cos(la) * np.sin((lo - b) / 2) ** 2))
    i = int(np.argmin(d))
    return ports.portname.iloc[i], ports.country.iloc[i], float(d[i])


def build() -> dict:
    snap = pd.read_csv(ROOT / "data/fleet/snapshot.csv")
    reg = pd.read_csv(ROOT / "data/reference/fleet_register.csv").drop_duplicates("vessel_key")
    uni = pd.read_csv(ROOT / "data/reference/universe.csv").set_index("id")["name"]
    ports = pd.read_csv(ROOT / "data/reference/ports.csv").dropna(subset=["lat", "lon"])
    # A name match counts only once the ship's own static report confirms it is a cargo ship or
    # tanker of ocean-going size; positions without a static report yet are held back.
    snap = snap[snap.ship_type.isna() | snap.ship_type.between(70, 89)]
    if "length" in snap:
        snap = snap[snap.length.isna() | (snap.length == 0) | (snap.length >= 100)]
    snap["confirmed"] = snap.ship_type.between(70, 89)
    snap = snap[snap.lat.between(-90, 90) & snap.lon.between(-180, 180) & ~((snap.lat == 0) & (snap.lon == 0))]
    df = snap.merge(reg, on="vessel_key", how="inner")
    ships = []
    for r in df.itertuples():
        port, country, nm = nearest_port(r.lat, r.lon, ports)
        sog = float(r.sog) if pd.notna(r.sog) and r.sog < 102.3 else None
        stopped = sog is not None and sog < 1
        state = "in port" if stopped and nm <= 5 else "idle" if stopped else "underway"
        hd = r.heading if pd.notna(r.heading) and r.heading < 360 else (r.cog if pd.notna(r.cog) and r.cog < 360 else None)
        ships.append({
            "name": r.vessel, "mmsi": int(r.mmsi), "imo": int(r.imo) if pd.notna(r.imo) and r.imo > 0 else None,
            "owner": uni.get(r.universe_id, r.universe_id), "ticker": r.universe_id, "segment": r.segment,
            "cls": str(r.vessel_class).replace("_", " ") if pd.notna(r.vessel_class) else "",
            "dwt": int(r.dwt) if pd.notna(r.dwt) else None, "built": int(r.built) if pd.notna(r.built) else None,
            "lat": round(float(r.lat), 4), "lon": round(float(r.lon), 4), "sog": sog,
            "hdg": float(hd) if hd is not None else None, "state": state,
            "dest": r.destination if isinstance(r.destination, str) and r.destination.strip() else None,
            "draught": float(r.draught) if pd.notna(r.draught) and r.draught > 0 else None,
            "near": f"{port}, {country}", "confirmed": bool(r.confirmed), "near_nm": round(nm, 1), "seen": r.time_utc,
        })
    reg_counts = reg.groupby("segment").size().to_dict()
    top = ports.sort_values("vessel_count_total", ascending=False).head(160)
    plist = [[r.portname, round(r.lat, 3), round(r.lon, 3)] for r in top.itertuples()]
    return {"ships": ships, "ports": plist, "register": int(len(reg)), "register_by_segment": reg_counts,
            "as_of": max(s["seen"] for s in ships), "owners": int(reg.universe_id.nunique())}


def kml(data: dict) -> str:
    col = {"dry_bulk": "ff0f77d2", "tankers": "ffd6782a", "containers": "ff7aa51b", "gas": "ff9c4ab0"}
    styles = "".join(f'<Style id="{k}"><IconStyle><color>{v}</color><scale>0.8</scale><Icon><href>'
                     f'http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png</href></Icon></IconStyle></Style>'
                     for k, v in col.items())
    folders = []
    for seg, label in SEG.items():
        pm = []
        for s in [x for x in data["ships"] if x["segment"] == seg]:
            desc = (f"{s['owner']} ({s['ticker']})<br/>{s['cls']} · {s['dwt'] or '–'} dwt · built {s['built'] or '–'}<br/>"
                    f"{s['state']} · {s['sog'] if s['sog'] is not None else '–'} kn<br/>near {s['near']}<br/>"
                    f"destination {s['dest'] or '–'}<br/>seen {s['seen']} UTC")
            pm.append(f"<Placemark><name>{escape(s['name'])}</name><styleUrl>#{seg}</styleUrl>"
                      f"<description><![CDATA[{desc}]]></description>"
                      f"<Point><coordinates>{s['lon']},{s['lat']},0</coordinates></Point></Placemark>")
        folders.append(f"<Folder><name>{label}</name>{''.join(pm)}</Folder>")
    return ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f"<name>FleetWatch {data['as_of'][:10]}</name>{styles}{''.join(folders)}</Document></kml>")


def main() -> None:
    data = build()
    OUT.mkdir(parents=True, exist_ok=True)
    html = TEMPLATE.read_text()
    html = html.replace("/*__FLEET__*/null", json.dumps(data, separators=(",", ":")))
    html = html.replace("/*__WORLD__*/null", WORLD.read_text())
    (ROOT / "data" / "cache").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "cache" / "fleet_map_artifact.html").write_text(html)  # body-only version for publishing
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'
            + html + "</body></html>")
    (OUT / "index.html").write_text(page)
    (OUT / "fleetwatch.kml").write_text(kml(data))
    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
         "properties": {k: v for k, v in s.items() if k not in ("lat", "lon")}} for s in data["ships"]]}
    (OUT / "fleet.geojson").write_text(json.dumps(gj))
    st = pd.Series([s["state"] for s in data["ships"] if s["confirmed"]]).value_counts().to_dict()
    print(sum(s["confirmed"] for s in data["ships"]), "confirmed")
    print(len(data["ships"]), "ships on the map", st, "as of", data["as_of"])


if __name__ == "__main__":
    main()
