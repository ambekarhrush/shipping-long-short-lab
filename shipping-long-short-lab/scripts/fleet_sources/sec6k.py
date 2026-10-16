import re
import time

import requests

UA = {"User-Agent": "Hrush Ambekar research ambekar2709@gmail.com"}
def recent(cik, forms=("6-K",), n=40):
    s = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=UA, timeout=60).json()["filings"]["recent"]
    return [dict(date=s["filingDate"][i], form=s["form"][i], acc=s["accessionNumber"][i]) for i in range(len(s["form"])) if s["form"][i] in forms][:n]
def docs(cik, acc):
    a = acc.replace("-", "")
    idx = requests.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/index.json", headers=UA, timeout=60).json()
    time.sleep(0.15)
    return [f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/{x['name']}" for x in idx["directory"]["item"] if x["name"].lower().endswith((".htm", ".html"))]
def find(cik, pattern, n=40):
    for f in recent(cik, n=n):
        for u in docs(cik, f["acc"]):
            h = requests.get(u, headers=UA, timeout=60).text; time.sleep(0.15)
            if re.search(pattern, h, re.I):
                return f, u, h
    return None
if __name__ == "__main__":
    r = find(1318885, r"fleet employment")
    print(r[0], r[1], len(r[2])); open("annual/DSX_fleet.htm", "w").write(r[2])
