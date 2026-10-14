import json
import pathlib
import time

import requests

UA = {"User-Agent": "Hrush Ambekar research ambekar2709@gmail.com"}
ciks = json.load(open("ciks.json"))
out = pathlib.Path("annual"); out.mkdir(exist_ok=True)
meta = {}
for t, cik in ciks.items():
    s = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=UA, timeout=60).json()
    r = s["filings"]["recent"]
    hits = [i for i, f in enumerate(r["form"]) if f in ("20-F", "10-K", "40-F")]
    if not hits:
        print(t, "no annual", set(r["form"][:30])); continue
    i = hits[0]
    acc = r["accessionNumber"][i].replace("-", ""); doc = r["primaryDocument"][i]
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
    p = out / f"{t}.htm"
    if not p.exists():
        p.write_bytes(requests.get(url, headers=UA, timeout=120).content); time.sleep(0.3)
    meta[t] = {"form": r["form"][i], "filed": r["filingDate"][i], "period": r["reportDate"][i], "url": url}
    print(t, meta[t]["form"], meta[t]["filed"], p.stat().st_size)
json.dump(meta, open("annual_meta.json", "w"), indent=1)
