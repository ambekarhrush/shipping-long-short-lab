"""Download (or refresh) every price series in the universe register plus benchmarks."""

import sys

from shiplab import prices
from shiplab.universe import load_register

BENCHMARKS = ["SPY", "BDRY", "BWET", "NOK=X", "OSEBX.OL", "^IRX"]

refresh = "--refresh" in sys.argv
reg = load_register()
todo = [("yahoo", b) for b in BENCHMARKS]
todo += sorted({(r.source, r.symbol) for r in reg.itertuples() if r.source in ("yahoo", "tiingo")})
for src, sym in todo:
    try:
        df = prices.load(src, sym, refresh=refresh)
        print(f"ok   {src:6s} {sym:10s} {df.index[0].date()} -> {df.index[-1].date()} n={len(df)}")
    except Exception as exc:
        print(f"FAIL {src:6s} {sym:10s} {type(exc).__name__}: {str(exc)[:80]}")
