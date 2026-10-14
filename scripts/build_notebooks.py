"""Build and execute the research notebooks from source (cells kept short; logic in src/)."""

import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"


def md(s):
    return nbf.v4.new_markdown_cell(s.strip())


def code(s):
    return nbf.v4.new_code_cell(s.strip())


def nb01():
    return [
        md("""
# 01 · Universe and data audit

**Purpose.** Before any signal is tested, establish *what can honestly be tested*: which
companies belonged to the opportunity set on each date, which of them have recoverable
price histories from free sources, and which vendor errors would otherwise contaminate
the results.

**Rules applied here and carried through the project**
1. *Point-in-time membership.* A company is in the universe only between the dates it was
   a listed pure-play in its segment. Merged, bankrupt and taken-private names stay in.
2. *Total returns are rebuilt, not downloaded.* Return = (price + cash distribution) /
   previous price, with split ratios applied explicitly. Vendor "adjusted close" series
   miss liquidating and special distributions.
3. *Official FX.* NOK-listed returns are converted with the Federal Reserve H.10 rate.
4. *No trade, no return.* Zero-volume days are stale quotes, not 0% returns.
5. *Takeover freeze.* From the first public bid, a stock trades on deal terms; no new
   signals are taken on it.
"""),
        code("""
import pandas as pd, matplotlib.pyplot as plt
from shiplab import panel, charts, prices, screens, qa
from shiplab.universe import load_register, membership, deal_frozen
pd.set_option("display.max_rows", 80, "display.width", 140)
reg = load_register()
p = panel.build()
member = membership(p.total_return.index)
inv = screens.investable(p, frozen=deal_frozen(p.total_return.index))
print(f"Register: {len(reg)} companies | tradable with data: {len(p.raw)} | "
      f"download failures: {len(p.failures)}")
"""),
        md("## 1. The opportunity set, including the companies that no longer exist"),
        code("""
first = p.total_return.apply(lambda s: s.first_valid_index()).dropna()
fig = charts.universe_timeline(reg, p.total_return.index, first)
charts.save(fig, "01_universe_timeline"); plt.show()
"""),
        code("""
summary = (reg.assign(status=lambda d: d["exit_type"].where(d["include"], "data gap / excluded"))
              .groupby(["segment", "status"]).size().unstack(fill_value=0))
summary
"""),
        md("## 2. Survivorship: how much a survivor-only backtest would overstate"),
        code("""
fig, gap = charts.survivorship(p.total_return, reg)
charts.save(fig, "01_survivorship"); plt.show()
"""),
        md("## 3. Vendor errors found and fixed"),
        code("""
fig = charts.fx_glitch(prices.load("yahoo", "NOK=X")["close"], prices.fred("DEXNOUS"))
charts.save(fig, "01_fx_glitch"); plt.show()
"""),
        code("""
print("Bad prints collapsed (spike fully reversed next day):")
display(p.repairs)
print("Remaining single-day moves beyond ±40% (each checked; real events or micro-caps "
      "removed by the liquidity screen):")
display(qa.extreme_moves(p.total_return, 0.4))
"""),
        md("## 4. Coverage"),
        code("""
cov = qa.coverage(p.total_return, member)
cov.join(reg.set_index("id")[["segment", "source"]]).query("expected_days > 0").head(15)
"""),
        md("## 5. Liquidity and breadth: where segment-neutral trading is feasible"),
        code("""
fig = charts.adv_by_segment(p.dollar_volume, member, reg)
charts.save(fig, "01_liquidity"); plt.show()
fig = charts.breadth(inv, reg)
charts.save(fig, "01_breadth"); plt.show()
"""),
        code("""
seg = reg.set_index("id")["segment"]
counts = inv.resample("ME").last().T.groupby(seg).sum().T
feasible = (counts >= 4)
feasible.resample("YE").mean().round(2).rename(columns=str).loc["2011":]
"""),
    ]


BUILDERS = {"01_universe_and_data": nb01}

if __name__ == "__main__":
    names = sys.argv[1:] or list(BUILDERS)
    for name in names:
        nb = nbf.v4.new_notebook()
        nb.cells = BUILDERS[name]()
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3",
                                     "language": "python"}
        NotebookClient(nb, timeout=900, kernel_name="python3",
                       resources={"metadata": {"path": str(NB)}}).execute()
        nbf.write(nb, NB / f"{name}.ipynb")
        print("built", name)
