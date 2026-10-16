"""Pre-registered test of H1 (docs/PREREGISTRATION_FLEET_HISTORY.md): idle share vs next-month
within-segment returns, 2016-01 to 2025-12. Run once; results to data/results/fleet_history_*."""

import json
import warnings

import numpy as np
import pandas as pd

from shiplab import metrics, panel, research
from shiplab.config import DATA
from shiplab.fleet import history
from shiplab.universe import tradable

warnings.filterwarnings("ignore")
OUT = DATA / "results"

sd = history.ship_days()
sd.to_parquet(DATA / "cache" / "fleet_history_shipdays.parquet")
sig = history.monthly_signals(sd)
idle = sig["idle_share"]
obs = sig["obs"]

p = panel.build()
seg = tradable().set_index("id")["segment"]
m_ret = (1 + p.total_return.fillna(0)).resample("ME").prod() - 1
m_ret = m_ret.where(p.total_return.resample("ME").count() > 10)
fwd = m_ret.shift(-1)

S, E = "2016-01-31", "2025-12-31"
rows, ls = [], []
for d in idle.loc[S:E].index:
    rets = []
    for s in ("dry_bulk", "tankers"):
        names = [c for c in idle.columns if seg.get(c) == s and pd.notna(idle.at[d, c]) and c in fwd.columns
                 and pd.notna(fwd.at[d, c])]
        if len(names) < 4:
            continue
        x = -idle.loc[d, names]                      # registered sign: low idle share -> long
        y = fwd.loc[d, names]
        rows.append({"date": d, "segment": s, "n": len(names), "ic": x.rank().corr(y.rank())})
        k = max(1, len(names) // 3)
        o = x.sort_values()
        rets.append(y[o.index[-k:]].mean() - y[o.index[:k]].mean())
    if rets:
        ls.append({"date": d + pd.offsets.MonthEnd(1), "ret": float(np.mean(rets))})

ic = pd.DataFrame(rows)
lsr = pd.DataFrame(ls).set_index("date")["ret"]
by = ic.groupby("segment")["ic"].agg(["mean", "count", "std"])
by["t"] = by["mean"] / by["std"] * np.sqrt(by["count"])
allic = ic.groupby("date")["ic"].mean()
res = {
    "months": int(allic.count()),
    "mean_ic": float(allic.mean()),
    "t_stat": float(allic.mean() / allic.std() * np.sqrt(allic.count())),
    "by_segment": by.round(4).to_dict("index"),
    "long_short_ann_return": float((1 + lsr).prod() ** (12 / len(lsr)) - 1),
    "long_short_sharpe": float(lsr.mean() / lsr.std() * np.sqrt(12)),
    "avg_names_per_segment_month": float(ic["n"].mean()),
    "note": "Gross of costs; equal-weight thirds; monthly. Pre-registered sign; run once.",
}
# log as research trial (monthly returns -> daily-equivalent sharpe for the DSR ledger)
research.log_trial("FLEETHIST_H1_idle_share", {"prereg": "docs/PREREGISTRATION_FLEET_HISTORY.md"}, S, E,
                   lsr, tag="research", periods_per_year=12)
json.dump(res, open(OUT / "fleet_history_h1.json", "w"), indent=1, default=float)
ic.to_csv(OUT / "fleet_history_ic.csv", index=False)
lsr.to_csv(OUT / "fleet_history_longshort.csv")
sig.to_parquet(OUT / "fleet_history_signals.parquet")
print(json.dumps(res, indent=1, default=float))
