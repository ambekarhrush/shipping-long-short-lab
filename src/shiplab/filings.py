"""Filings analyser: what shipping companies say in their results releases, quarter by quarter.

Reads the releases saved by scripts/pull_filings.py and extracts, with deterministic patterns
(no model calls, so every number can be traced to a sentence):

* forward_pct, forward_rate  share of next-quarter days already fixed and the average rate
                             ("approximately 71% of ... days ... fixed at ... $30,112 per day")
* tce                        realised fleet time-charter-equivalent rate for the quarter
* fleet_size                 number of vessels in the fleet as stated
* dividend                   dividend per share declared
* net_income_m               net income for the quarter, $ millions (negative for a loss)

Each field keeps the sentence it came from (`*_src`) so the extraction can be audited. Then:

* `changes()` flags quarter-on-quarter moves an analyst would want to see first: forward rate
  vs last quarter's realised TCE, coverage up or down, dividend cut or raise, fleet growth, swing
  to a loss.
* `event_study()` tests whether the booking surprise (forward rate / realised TCE - 1) predicts
  the stock's return relative to its segment over the 20 trading days after the release.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA

RELEASES = DATA / "filings" / "releases"
NUM = r"\$\s?([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,6})(?:\.[0-9]+)?"
SENT = re.compile(r"(?<=[.;•●])\s+|\n(?=[A-Z●•])")


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def sentences(text: str) -> list[str]:
    t = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.;])\s+(?=[A-Z●•(])|[●•]", t) if 20 < len(s.strip()) < 900]


FWD = re.compile(r"(\d{1,3}(?:\.\d)?)\s?%\s+of\s+(?:the\s+|its\s+|our\s+|total\s+|its\s+total\s+|the\s+company(?:'|’)s\s+)?"
                 r"[^.%]{0,90}?\b(?:days|capacity)\b", re.I)
FWD_VERB = re.compile(r"\b(fixed|booked|covered|secured|contracted|employed at)\b", re.I)
TCE = re.compile(r"(?:time charter equivalent|TCE)[^.$]{0,120}?" + NUM + r"[^.]{0,20}?(?:per day|/day|per vessel per day)", re.I)
FLEET = re.compile(r"fleet (?:of|consists of|comprises|comprising|totals?)\s+(?:approximately\s+)?(\d{1,3})\s+(?:\w+\s+){0,3}?(?:vessels|ships|tankers|carriers|containerships|dry bulk)", re.I)
DIV = re.compile(r"(?:dividend|distribution)[^.$]{0,80}?\$\s?(\d{1,2}\.\d{2,3})\s+per\s+(?:common\s+|ordinary\s+)?share", re.I)
NI = re.compile(r"net (income|loss|profit)(?: attributable to [^.$]{0,40})?\s+(?:of|was|amounted to|totall?ing|totaled)\s+\$\s?(\d{1,4}(?:\.\d+)?)\s*(million|m\b|thousand)", re.I)
QTR = re.compile(r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\s+quarter\s+(?:of\s+|ended\s+[A-Za-z]+\s+\d{1,2},\s+)?(20\d\d)", re.I)
QMAP = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4}


def reported_quarter(text: str, filed: pd.Timestamp) -> pd.Period:
    """Quarter the release reports on: the first 'Nth quarter of YYYY' in the headline area that
    is not after the filing date; fall back to the quarter before the filing."""
    for m in QTR.finditer(text[:3000]):
        q = pd.Period(f"{m.group(2)}Q{QMAP[m.group(1).lower()]}", "Q")
        if q.end_time < filed and q >= (pd.Period(filed, "Q") - 2):
            return q
    return pd.Period(filed, "Q") - 1


def extract(text: str) -> dict:
    out: dict = {}
    ss = sentences(text)
    # forward bookings: prefer a fleet-wide statement ("total", "fleet", "combined") in the first match set
    cands = []
    for s in ss:
        if not FWD_VERB.search(s) or "%" not in s:
            continue
        m, r = FWD.search(s), re.search(NUM, s)
        if m and r and re.search(r"per day|/day|USD/day|daily|TCE", s, re.I):
            pct, rate = float(m.group(1)), _num(r.group(1))
            if 1 <= pct <= 100 and 2_000 <= rate <= 400_000:
                score = bool(re.search(r"total|fleet|combined|company", s, re.I))
                cands.append((score, pct, rate, s))
    if cands:
        best = sorted(cands, key=lambda c: -c[0])[0]
        out.update(forward_pct=best[1], forward_rate=best[2], forward_src=best[3][:400])
    for s in ss:
        m = TCE.search(s)
        if m and "quarter" in s.lower() and not FWD_VERB.search(s):
            v = _num(m.group(1))
            if 2_000 <= v <= 400_000:
                out.update(tce=v, tce_src=s[:400])
                break
    m = FLEET.search(text)
    if m and 2 <= int(m.group(1)) <= 400:
        out.update(fleet_size=int(m.group(1)), fleet_src=m.group(0)[:200])
    m = DIV.search(text)
    if m:
        out.update(dividend=float(m.group(1)), dividend_src=m.group(0)[:200])
    m = NI.search(text[:12000])
    if m:
        v = float(m.group(2)) / (1000 if m.group(3).lower() == "thousand" else 1)
        out.update(net_income_m=-v if m.group(1).lower() == "loss" else v, net_income_src=m.group(0)[:200])
    return out


def table(root: Path = RELEASES) -> pd.DataFrame:
    """One row per company-quarter (the most informative release if several were filed)."""
    rows = []
    for f in sorted(root.glob("*/*.txt")):
        filed, acc = f.name.split("_")[:2]
        text = f.read_text(errors="ignore")
        if len(text) < 2500:
            continue
        filed = pd.Timestamp(filed)
        rec = {"company": f.parent.name, "filed": filed, "accession": acc, "file": f.name,
               "quarter": reported_quarter(text, filed), **extract(text)}
        rec["n_fields"] = sum(k in rec for k in ("forward_rate", "tce", "fleet_size", "dividend", "net_income_m"))
        rows.append(rec)
    d = pd.DataFrame(rows)
    d = d.sort_values(["company", "quarter", "n_fields", "filed"]).groupby(["company", "quarter"]).tail(1)
    return d.sort_values(["company", "quarter"]).reset_index(drop=True)


def changes(t: pd.DataFrame) -> pd.DataFrame:
    """Quarter-on-quarter flags per company."""
    out = []
    for c, g in t.groupby("company"):
        g = g.sort_values("quarter").copy()
        g["booking_surprise"] = g.forward_rate / g.tce - 1
        g["forward_vs_last_forward"] = g.forward_rate / g.forward_rate.shift(1) - 1
        g["tce_qoq"] = g.tce / g.tce.shift(1) - 1
        g["dividend_change"] = g.dividend - g.dividend.shift(1)
        g["fleet_change"] = g.fleet_size - g.fleet_size.shift(1)
        g["coverage_change_pp"] = g.forward_pct - g.forward_pct.shift(1)
        flags = []
        for r in g.itertuples():
            f = []
            if pd.notna(r.booking_surprise) and abs(r.booking_surprise) >= 0.15:
                f.append(f"next-quarter bookings {r.booking_surprise:+.0%} vs this quarter's TCE")
            if pd.notna(r.dividend_change) and r.dividend_change != 0:
                f.append(f"dividend {'raised' if r.dividend_change > 0 else 'cut'} to ${r.dividend:.2f}")
            if pd.notna(r.fleet_change) and abs(r.fleet_change) >= 2:
                f.append(f"fleet {int(r.fleet_change):+d} vessels to {int(r.fleet_size)}")
            if pd.notna(r.coverage_change_pp) and abs(r.coverage_change_pp) >= 15:
                f.append(f"coverage {r.coverage_change_pp:+.0f} pp")
            flags.append("; ".join(f))
        g["flags"] = flags
        out.append(g)
    return pd.concat(out, ignore_index=True)


def event_study(ch: pd.DataFrame, total_return: pd.DataFrame, segment: pd.Series, horizon: int = 20) -> pd.DataFrame:
    """Return of each stock minus its segment basket from the day after the release to +horizon."""
    r = total_return.fillna(0)
    lr = np.log1p(r)
    seg_mean = {s: np.log1p(r[[c for c in r.columns if segment.get(c) == s]].mean(axis=1)) for s in segment.unique()}
    rows = []
    for x in ch.dropna(subset=["booking_surprise"]).itertuples():
        if x.company not in r.columns:
            continue
        idx = r.index.searchsorted(x.filed, side="right")   # first full trading day after filing
        if idx + horizon > len(r.index):
            continue
        sl = slice(idx, idx + horizon)
        own = lr[x.company].iloc[sl].sum()
        bench = seg_mean[segment[x.company]].iloc[sl].sum()
        rows.append({"company": x.company, "quarter": str(x.quarter), "filed": x.filed,
                     "segment": segment[x.company], "booking_surprise": x.booking_surprise,
                     "excess_return": float(np.expm1(own - bench))})
    return pd.DataFrame(rows)
