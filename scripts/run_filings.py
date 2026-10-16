"""Filings analyser end to end: extract -> quarter-on-quarter flags -> event study.

Pre-specified test (written before looking at returns, see 05-filings-analyser/README.md):
booking surprise = forward booked rate / realised TCE of the reported quarter - 1; sign positive;
outcome = stock return minus its segment basket over the 20 trading days after the release.
"""
import json
import warnings

import numpy as np
import pandas as pd

from shiplab import filings, panel, research
from shiplab.config import DATA
from shiplab.universe import tradable

warnings.filterwarnings("ignore")
OUT = DATA / "results"
t = filings.table()
ch = filings.changes(t)
keep = ["company", "quarter", "filed", "forward_pct", "forward_rate", "tce", "booking_surprise", "fleet_size",
        "dividend", "net_income_m", "flags", "forward_src", "tce_src", "fleet_src", "dividend_src", "net_income_src", "file"]
ch["quarter"] = ch["quarter"].astype(str)
ch[keep].to_csv(OUT / "filings_extracted.csv", index=False)

cov = t[["forward_rate", "tce", "fleet_size", "dividend", "net_income_m"]].notna().mean().round(3).to_dict()
p = panel.build()
seg = tradable().set_index("id")["segment"]
ev = filings.event_study(ch, p.total_return, seg)
ev.to_csv(OUT / "filings_event_study.csv", index=False)
x, y = ev.booking_surprise.clip(-1, 1), ev.excess_return
ic = x.rank().corr(y.rank())
n = len(ev)
t_ic = ic * np.sqrt((n - 2) / (1 - ic ** 2)) if n > 3 else np.nan
hi, lo = ev[x > 0.05], ev[x < -0.05]
res = {"releases": int(len(t)), "companies": int(t.company.nunique()),
       "quarters": [str(t.quarter.min()), str(t.quarter.max())], "field_coverage": cov,
       "events": n, "rank_ic": ic, "t_stat": t_ic,
       "mean_excess_when_surprise_above_5pct": hi.excess_return.mean(), "n_above": len(hi),
       "mean_excess_when_surprise_below_minus_5pct": lo.excess_return.mean(), "n_below": len(lo),
       "note": "20 trading days after release, return minus segment basket; pre-specified sign positive"}
# daily-equivalent series for the trial ledger: equal-weight long-high / short-low event returns by month
m = ev.assign(side=np.sign(x.where(x.abs() > 0.05, 0)), month=ev.filed.dt.to_period("M").dt.to_timestamp("M"))
m = m[m.side != 0].groupby("month").apply(lambda g: (g.side * g.excess_return).mean())
research.log_trial("FILINGS_booking_surprise_20d", {"horizon": 20, "threshold": 0.05}, str(ev.filed.min().date()),
                   str(ev.filed.max().date()), m, tag="research", periods_per_year=12)
json.dump(res, open(OUT / "filings_summary.json", "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
latest = ch.sort_values("filed").groupby("company").tail(1)
print(latest[latest["flags"] != ""][["company", "quarter", "flags"]].to_string())
