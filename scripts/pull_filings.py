"""Download quarterly results press releases for every SEC-filing name in the live universe.

Source: EDGAR full-text search (free, no key). Foreign private issuers file results as 6-K
exhibits; US domestic filers (GNK, INSW, LPG...) as 8-K exhibit 99.1. Each release is stored
as plain text in data/filings/releases/<id>/<filed>_<accession>.txt so extraction is
reproducible offline.

    python scripts/pull_filings.py            # since 2019
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "filings" / "releases"
UA = {"User-Agent": "Hrush Ambekar independent research ambekar2709@gmail.com"}
QUERY = '"quarter" "net income" "results"'


def ciks() -> dict[str, int]:
    t = requests.get("https://www.sec.gov/files/company_tickers.json", headers=UA, timeout=60).json()
    t = {v["ticker"]: v["cik_str"] for v in t.values()}
    u = pd.read_csv(ROOT / "data/reference/universe.csv")
    u = u[(u.include == 1) & u.end.isna()]
    return {r.id: t[r.symbol] for r in u.itertuples() if r.symbol in t}


def search(cik: int, start: str) -> list[dict]:
    hits, frm = [], 0
    while True:
        r = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params=dict(q=QUERY, forms="6-K,8-K", ciks=f"{cik:010d}", dateRange="custom",
                        startdt=start, enddt=pd.Timestamp.today().strftime("%Y-%m-%d"), **{"from": frm}),
            headers=UA, timeout=60).json()["hits"]
        page = r["hits"]
        hits += page
        frm += len(page)
        time.sleep(0.2)
        if not page or frm >= r["total"]["value"]:
            return hits


def is_release(text: str) -> bool:
    head = text[:4000].lower()
    return bool(re.search(r"(first|second|third|fourth|1st|2nd|3rd|4th|q[1-4])[\s\-]*quarter|six months|nine months|full[\s\-]year", head)) \
        and bool(re.search(r"results|reports|announces", head))


def _text(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=90)
    time.sleep(0.12)
    if url.lower().endswith(".pdf"):
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(r.content)
            f.flush()
            return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
    return BeautifulSoup(r.text, "lxml").get_text(" ")


def walk(uid: str, cik: int, start: str) -> int:
    """Second pass: every 6-K/8-K in the submissions history, including PDF exhibits, which
    full-text search does not index (Frontline, for example, files its results as PDF)."""
    sub = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=UA, timeout=60).json()
    blocks = [sub["filings"]["recent"]] + [
        requests.get(f"https://data.sec.gov/submissions/{f['name']}", headers=UA, timeout=60).json()
        for f in sub["filings"].get("files", [])]
    d = OUT / uid
    have = {p.name.split("_")[1] for p in d.glob("*.txt")}
    n = 0
    for b in blocks:
        for form, date, acc in zip(b["form"], b["filingDate"], b["accessionNumber"]):
            if form not in ("6-K", "8-K") or date < start or acc in have:
                continue
            a = acc.replace("-", "")
            try:
                idx = requests.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/index.json", headers=UA, timeout=60).json()
            except Exception:  # noqa: BLE001
                continue
            time.sleep(0.12)
            for it in idx["directory"]["item"]:
                nm = it["name"]
                if not nm.lower().endswith((".htm", ".html", ".pdf")) or "index" in nm.lower() or re.match(r"R\d+\.htm", nm):
                    continue
                try:
                    text = _text(f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/{nm}")
                except Exception:  # noqa: BLE001
                    continue
                text = re.sub(r"[ \t\xa0]+", " ", text)
                text = re.sub(r"\s*\n\s*", "\n", text)
                if len(text) > 3000 and is_release(text):
                    (d / f"{date}_{acc}_{Path(nm).stem}.txt").write_text(text)
                    n += 1
    return n


def main(start="2019-01-01") -> None:
    for uid, cik in ciks().items():
        d = OUT / uid
        d.mkdir(parents=True, exist_ok=True)
        n = 0
        for h in search(cik, start):
            acc, fname = h["_id"].split(":")
            if not fname.lower().endswith((".htm", ".html", ".txt")):
                continue
            path = d / f"{h['_source']['file_date']}_{acc}_{Path(fname).stem}.txt"
            if path.exists():
                n += 1
                continue
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{fname}"
            try:
                html = requests.get(url, headers=UA, timeout=60).text
            except Exception as e:  # noqa: BLE001
                print(uid, "fetch failed", url, e)
                continue
            time.sleep(0.12)
            text = BeautifulSoup(html, "lxml").get_text(" ")
            text = re.sub(r"[ \t\xa0]+", " ", text)
            text = re.sub(r"\s*\n\s*", "\n", text)
            if is_release(text):
                path.write_text(text)
                n += 1
        n += walk(uid, cik, start)
        print(uid, cik, n, "releases", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
