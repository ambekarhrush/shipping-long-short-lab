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

SETUP = """
import json, warnings
import pandas as pd, matplotlib.pyplot as plt
from IPython.display import Markdown, display
from shiplab import charts
from shiplab.config import DATA
warnings.filterwarnings("ignore")
pd.set_option("display.precision", 3, "display.width", 140)
R = DATA / "results"
perf = pd.read_csv(R / "performance_by_period.csv")
strat = pd.read_parquet(R / "strategy_returns.parquet")
bench = pd.read_parquet(R / "benchmark_returns.parquet")
dsr = json.load(open(R / "deflated_sharpe.json"))
def row(period, series="Strategy"):
    return perf[(perf.period == period) & (perf.series == series)].iloc[0]
"""

SUMMARY_TABLE = r'''
w, v, h = row("Walk-forward 2014-2020"), row("Validation 2021-2022"), row("Holdout 2023-")
fmt = lambda r: f"| {r.sharpe:.2f} | {r.ann_return:.1%} | {r.ann_vol:.1%} | {r.max_drawdown:.1%} | {r.beta:.2f} |"
p = dsr["deflated_sharpe_probability"]["Holdout 2023-"]
display(Markdown(
    "| Period | Sharpe | Annual return | Volatility | Max drawdown | Beta to S&P 500 |\n"
    "|---|---|---|---|---|---|\n"
    f"| Walk-forward 2014-2020 {fmt(w)}\n"
    f"| Validation 2021-2022 {fmt(v)}\n"
    f"| **Sealed holdout 2023-** {fmt(h)}\n\n"
    f"Deflated-Sharpe probability on the holdout after **{dsr['n_research_trials']} logged trials**: "
    f"**{p:.2f}**. Values above 0.95 would indicate skill with conventional confidence."))
'''


def nb00():
    return [
        md("""
# 03 · Market-neutral long/short: summary

*Independent research project. Not affiliated with, endorsed by or produced for any current,
previous or future employer of the author. Public data only. Not investment advice.*

**Question.** Can a market-neutral book of listed shipping equities earn returns from stock
selection, rather than from the direction of freight rates or the market? And if so, where
does the information edge actually come from?
"""),
        code(SETUP),
        code(SUMMARY_TABLE),
        code("""
fig = charts.equity_curve(strat["strategy"], {"S&P 500": bench["SPY"], "Shipping basket (EW)": bench["EW shipping basket"]})
plt.show()
"""),
        md("""
## Five findings

1. **Public freight data is priced within the week.** Segment equity baskets and their Baltic
   index move together contemporaneously; neither predicts the other a month out in dry bulk,
   with only a modest lag in tankers (project 02).
2. **Cheapness within a segment works; balance-sheet quality and freight timing do not, on their
   own.** Book-to-market inside each segment, and fading moves that are out of line with a
   stock's freight sensitivity, are the two signals that survive walk-forward testing (notebooks 01-04).
   A pre-registered hypothesis that balance-sheet strength pays only in falling freight markets
   was rejected and left rejected.
3. **The return is genuinely market-neutral** (beta near zero, low correlation to the shipping
   basket) and positive in the 2016 trough and the Red Sea disruption, but it gave back about 5%
   in the 2026 Hormuz crisis (notebooks 05, 07).
4. **Capacity is the binding constraint.** These stocks trade a few million dollars a day.
   Sharpe is roughly 0.6-0.8 up to USD 25m and dollar alpha plateaus below USD 1m a year (notebook 06).
5. **After correcting for the search, the public-data edge is not statistically distinguishable
   from luck.** That points to where an edge must come from: company-specific operating
   information that reaches the market late. FleetWatch (project 04) tracks ~1,000 named ships
   of 21 listed owners for exactly that, with every estimate committed to git before the
   companies report.
"""),
        md("""
## The four projects

| Project | Question |
|---|---|
| [01 Data foundation](../../01-data-foundation) | Can you trust free shipping-equity data? |
| [02 Freight priced by Friday](../../02-freight-priced-by-friday) | Does public freight data predict shipping stocks? |
| [03 Market-neutral long/short](../../03-market-neutral-long-short) | Is there stock-selection alpha from public data? (this project) |
| [04 FleetWatch](../../04-fleetwatch) | Can ship-level tracking of each owner's fleet give an edge? |

Detail notebooks in this project: 01 signals, 02-04 the three sleeves, 05 portfolio and risk,
06 robustness, 07 stress windows.
"""),
    ]


def nb02():
    return [
        md("""
# 02 · Fifteen years of shipping

Shipping equities are levered, cyclical claims on a handful of observable variables. Before
testing any strategy, this notebook shows what 2011-2026 looked like, how widely stocks in the
same segment diverged, and how quickly equity prices absorb public freight data.
"""),
        code("""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, matplotlib.pyplot as plt
from shiplab import charts, research, signals
from shiplab.config import DATA
inp = research.Inputs()
baskets = signals.segment_baskets(inp.tr.where(inp.inv), inp.seg)
"""),
        md("## Equities against freight"),
        code('fig = charts.freight_vs_equity(inp.fr, baskets); charts.save(fig, "02_fifteen_years"); plt.show()'),
        md("""
The equity baskets and their freight indices share cycles but not levels: equity returns also
carry dilution, leverage, newbuilding and capital-allocation decisions, which differ by company.
That is the opening for stock selection.
"""),
        md("## Same freight, different outcomes"),
        code('fig = charts.dispersion(inp.tr, inp.inv, inp.seg); charts.save(fig, "02_dispersion"); plt.show()'),
        md("## How fast is freight priced?"),
        code("""
ll = pd.read_csv(DATA / "results" / "lead_lag.csv", index_col=0)
fig = charts.lead_lag(ll); charts.save(fig, "02_lead_lag"); plt.show()
ll.round(3).T
"""),
        md("""
The peak is at lag zero: the equity market and the Baltic indices move in the same week. There
is no exploitable lead from public freight indices to dry bulk equities, and only a small one in
tankers. **Any edge from freight information therefore has to come before it is public** - the
premise of FleetWatch (project 04).
"""),
        md("## Does aggregate ship-tracking data do better?"),
        code("""
pwf = pd.read_csv(DATA / "results" / "portwatch_vs_freight.csv")
fig = charts.portwatch_vs_freight(pwf); charts.save(fig, "02_portwatch"); plt.show()
pwf.round(3)
"""),
        md("""
No. Chokepoint transit data from the IMF's PortWatch (built from satellite AIS) moves with
freight in the same month at most, and predicts nothing a month ahead. Aggregate AIS describes
the market everyone already sees; its value, if any, lies in attributing ships to companies.
"""),
    ]


def nb03():
    return [
        md("""
# 03 · Signals

All signals are evaluated at the close of day *t* using information available then, and ranked
**within segment** so the book never bets on one segment against another.

| Signal | Definition | Data |
|---|---|---|
| Value | book equity / market cap (as-traded price x shares) | SEC XBRL, entered the day after filing |
| Strength | equity / total assets | SEC XBRL |
| Freight-beta momentum | rolling freight beta x 63-day change in the segment freight index | Baltic indices |
| Residual | 10/20-day cumulative return unexplained by freight + market, z-scored | Baltic indices, SPY |
"""),
        code("""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from shiplab import research, style
inp = research.Inputs()
z_v, z_s, z_f = research.factor_z(inp)
fwd = inp.tr.shift(-1).rolling(21).sum().shift(-20)   # next-month return
def ic(z, name):
    rows = []
    for s in sorted(inp.seg.unique()):
        cols = [c for c in z.columns if inp.seg[c] == s]
        m = z[cols].resample("ME").last(); f = fwd[cols].reindex(m.index)
        ok = m.notna().sum(axis=1) >= 4                      # months with 4+ ranked names
        x = m[ok].corrwith(f[ok], axis=1, method="spearman").loc["2011":"2022"].dropna()
        rows.append({"signal": name, "segment": s, "mean_IC": x.mean(), "months": len(x),
                     "t_stat": x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 else np.nan})
    return rows
ic_tab = pd.DataFrame(ic(z_v, "value") + ic(z_s, "strength") + ic(z_f, "freight_beta_momentum"))
ics = ic_tab.pivot(index="segment", columns="signal", values="mean_IC")
ic_tab.round(3)
"""),
        md("""
Average monthly rank correlation (information coefficient) between each signal and the next
month's return, within segment, 2011-2022, using only months with at least four ranked names.
With 4-10 names per segment, monthly ICs are noisy: read the t-statistic, not the size. Values of
0.03-0.05 with |t| above 2 would be typical of a tradable equity signal.
"""),
        code("""
style.apply()
fig, ax = plt.subplots(figsize=(9, 3.2))
ics.plot.bar(ax=ax, color=[style.INK, "#9CA3AF", style.SEGMENT_COLORS["tankers"]], width=0.75)
ax.axhline(0, color=style.INK, lw=0.8); ax.set_ylabel("Mean monthly rank IC")
ax.set_title("Signal strength by segment"); ax.tick_params(axis="x", rotation=0)
plt.show()
"""),
    ]


def sleeve_nb(name, title, intro):
    return [
        md(f"# {title}\n\n{intro}"),
        code(SETUP),
        code(f"""
from shiplab import metrics
grid = pd.read_parquet(R / "grid_returns.parquet")
picks = pd.read_csv(R / "walk_forward_picks.csv", index_col=0)
cols = [c for c in grid.columns if c.startswith("{name}")]
tab = pd.DataFrame({{c: metrics.summary(grid[c].loc["2011":"2022"]) for c in cols}}).T
display(tab[["ann_return", "ann_vol", "sharpe", "max_drawdown"]].round(3))
display(picks[["{name}"]].rename(columns={{"{name}": "chosen for the year (prior data only)"}}))
"""),
        code(f"""
from shiplab import style
style.apply()
fig, ax = plt.subplots(figsize=(10, 3.4))
for c in cols:
    ax.plot((1 + grid[c].loc["2011":"2022"]).cumprod(), color="#C4C8CE", lw=1)
if "sleeve_{name}" in strat:
    s = strat["sleeve_{name}"].dropna()
    ax.plot((1 + s).cumprod(), color=style.INK, lw=2)
ax.set_title("Every variant (grey) and the walk-forward path (black)")
plt.show()
"""),
    ]


def nb07():
    return [
        md("""
# 07 · Portfolio construction

* Sleeves are scaled to 6% ex-ante volatility each (trailing 63 days at current weights).
* Per-name cap 7.5% of NAV; gross cap 250%; at most 10% of a stock's 60-day median daily value.
* Residual market beta hedged with SPY; drawdown brake halves risk after a 15% drawdown.
* Costs: half-spread by liquidity tier plus square-root impact; borrow 0.5%-15% a year by tier.
* Targets set at the close of *t* are traded at the close of *t+1*.
"""),
        code(SETUP),
        code("""
from shiplab import style
expo = pd.read_parquet(R / "exposures.parquet")
style.apply()
fig, ax = plt.subplots(figsize=(10, 3.2))
e = expo.resample("W").mean()
ax.plot(e.index, e["gross"], color=style.INK, label="Gross")
ax.plot(e.index, e["net"], color=style.MUTED, label="Net (stocks)")
ax.plot(e.index, e["beta_before_hedge"], color=style.SEGMENT_COLORS["tankers"], label="Beta before SPY hedge")
ax.axhline(0, color=style.INK, lw=0.6); ax.legend(ncol=3, loc="upper left"); ax.set_title("Exposures (share of NAV)")
plt.show()
"""),
        code("""
att = pd.read_parquet(R / "attribution.parquet")
fig = charts.attribution_bars(att, len(att) / 252); charts.save(fig, "07_attribution"); plt.show()
(att.sum() / (len(att) / 252)).rename("contribution per year").to_frame().T.round(4)
"""),
    ]


def nb08():
    return [
        md("""
# 08 · Robustness

1. Every variant ever run is in `data/results/trials.csv`, written automatically.
2. Parameters were chosen each year using only earlier data (walk-forward).
3. The 2023+ holdout was sealed in code; the configuration was committed to git
   (`docs/PREREGISTRATION.md`) before the single run.
4. The deflated Sharpe ratio corrects the holdout Sharpe for the number of variants tried.
"""),
        code(SETUP),
        code("""
trials = pd.read_csv(R / "trials.csv")
fig = charts.trials_histogram(trials, row("Holdout 2023-").sharpe, dsr["deflated_sharpe_probability"]["Holdout 2023-"])
charts.save(fig, "08_trials"); plt.show()
trials.groupby("tag").size().rename("runs").to_frame().T
"""),
        code("""
cap = pd.read_csv(R / "capacity.csv")
fig = charts.capacity(cap); charts.save(fig, "08_capacity"); plt.show()
cap.round(3)
"""),
        code("""
perf[perf.series.isin(["Strategy", "EW shipping basket", "SPY", "BDRY", "BWET"])].pivot(
    index="series", columns="period", values="sharpe").round(2)
"""),
    ]


def nb09():
    return [
        md("""
# 09 · Stress windows

| Window | Dates | What happened |
|---|---|---|
| 2016 dry bulk trough | Nov 2015 - Jun 2016 | BDI record low; dilution and restructurings |
| COVID shock | Feb - May 2020 | Demand collapse, then a floating-storage spike in tankers |
| 2022 Russia sanctions | Feb - Dec 2022 | Tanker trade rerouted, product tanker boom |
| Red Sea disruption | Nov 2023 - Dec 2024 | Houthi attacks, Cape diversions, container rates spike |
| 2026 Hormuz crisis | 28 Feb 2026 - | Gulf transits halted after strikes on Iran; VLCC earnings above USD 400k/day |
"""),
        code(SETUP),
        code("""
stress = pd.read_csv(R / "stress.csv")
fig = charts.stress_bars(stress); charts.save(fig, "09_stress"); plt.show()
stress.pivot(index="window", columns="series", values="total_return").round(3)
"""),
        md("""
The 2026 Hormuz episode illustrates the project's thesis: the dispersion between tanker owners
depended on *where each company's ships were* when the strait closed - an exposure invisible in
filings and Baltic indices, and directly observable from AIS.
"""),
    ]


def nb10():
    return [
        md("""
# 10 · FleetWatch: ship-level tracking of the listed fleets

**What is proprietary here** is not raw AIS - large funds buy that - but the mapping from
named ships to listed owners, and the company-level operating estimates built on it for
small-cap names that few analysts model.

| Layer | Source | Status |
|---|---|---|
| Fleet register: company -> ship, DWT, built, employment | SEC 20-F/10-K fleet tables, Diana fleet employment 6-K, company fleet pages | ~1,000 operating ships, 21 owners |
| AIS identity (MMSI/IMO) | aisstream.io static reports | builds as the collector runs |
| Ship states: laden/ballast, underway/anchored/moored, region | AIS positions + draught, PortWatch port list | builds as the collector runs |
| Company signals: idle share, laden share, regional exposure | aggregation of ship states | forward-only, committed hourly |

Every estimate is written to git by a scheduled job before the company reports, so the live
record cannot be fitted afterwards.
"""),
        code("""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, matplotlib.pyplot as plt
from shiplab import style
from shiplab.config import DATA, REFERENCE
reg = pd.read_csv(REFERENCE / "fleet_register.csv")
op = reg[~reg.newbuild]
from shiplab import charts
fig = charts.fleet_register(reg); charts.save(fig, "04_fleet_register"); plt.show()
op.groupby(["segment", "universe_id"]).agg(ships=("vessel", "size"), dwt_m=("dwt", lambda x: x.sum() / 1e6),
                                           median_age=("built", lambda b: 2026 - b.median())).round(1)
"""),
        code("""
style.apply()
mix = op.pivot_table(index="universe_id", columns="vessel_class", values="dwt", aggfunc="sum").fillna(0)
mix = mix.div(mix.sum(axis=1), axis=0)
fig, ax = plt.subplots(figsize=(10, 5))
mix.sort_index().plot.barh(stacked=True, ax=ax, width=0.8, colormap="tab20")
ax.set_xlabel("Share of fleet deadweight")
ax.legend(ncol=4, fontsize=7, loc="lower center", bbox_to_anchor=(0.5, -0.32))
ax.set_title("What each listed owner actually operates"); plt.show()
"""),
        code("""
ident = DATA / "fleet" / "identity.csv"
sig = DATA / "fleet" / "company_signals.csv"
if ident.exists():
    display(pd.read_csv(ident)["status"].value_counts())
if sig.exists():
    display(pd.read_csv(sig).tail(20))
else:
    print("Live collection not yet started: signals appear here once the hourly collector has run.")
"""),
    ]


BUILDERS.update({
    "00_executive_summary": nb00,
    "02_fifteen_years_of_shipping": nb02,
    "03_signals": nb03,
    "04_sleeve_pairs": lambda: sleeve_nb(
        "pairs", "04 · Sleeve 1: pairs within a segment",
        "Mean reversion between similar companies, re-selected each quarter on a trailing year "
        "(correlation, cointegration test and a balance-sheet similarity filter). Enter at |z| of "
        "1.5-2, exit at 0.5, stop at 4, maximum 30 days. **Result: no reliable edge; excluded from "
        "the final book before the holdout.**"),
    "05_sleeve_factor": lambda: sleeve_nb(
        "factor", "05 · Sleeve 2: factor-ranked long/short",
        "Within each segment with at least four investable names: long the top ranks and short the "
        "bottom on a composite of value, balance-sheet strength and freight-beta momentum. "
        "Dollar-neutral per segment, inverse-volatility legs, weekly rebalance."),
    "06_sleeve_equity_vs_freight": lambda: sleeve_nb(
        "residual", "06 · Sleeve 3: equity versus freight",
        "Each stock is regressed on its segment freight index and the market over a trailing year; "
        "when its recent return departs from what that relationship implies, the sleeve trades it "
        "back, segment-neutral."),
    "07_portfolio_and_risk": nb07,
    "08_robustness": nb08,
    "09_stress_and_attribution": nb09,
    "10_fleetwatch": nb10,
})


# notebook -> (project folder, file name)
LAYOUT = {
    "01_universe_and_data": ("01-data-foundation", "universe_and_data_audit"),
    "02_fifteen_years_of_shipping": ("02-freight-priced-by-friday", "freight_vs_equities"),
    "00_executive_summary": ("03-market-neutral-long-short", "00_summary"),
    "03_signals": ("03-market-neutral-long-short", "01_signals"),
    "04_sleeve_pairs": ("03-market-neutral-long-short", "02_sleeve_pairs"),
    "05_sleeve_factor": ("03-market-neutral-long-short", "03_sleeve_factor"),
    "06_sleeve_equity_vs_freight": ("03-market-neutral-long-short", "04_sleeve_equity_vs_freight"),
    "07_portfolio_and_risk": ("03-market-neutral-long-short", "05_portfolio_and_risk"),
    "08_robustness": ("03-market-neutral-long-short", "06_robustness"),
    "09_stress_and_attribution": ("03-market-neutral-long-short", "07_stress_windows"),
    "10_fleetwatch": ("04-fleetwatch", "fleetwatch"),
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(BUILDERS)
    for name in names:
        nb = nbf.v4.new_notebook()
        nb.cells = BUILDERS[name]()
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3",
                                     "language": "python"}
        folder, fname = LAYOUT[name]
        out_dir = ROOT / folder / "notebooks"
        out_dir.mkdir(parents=True, exist_ok=True)
        NotebookClient(nb, timeout=900, kernel_name="python3",
                       resources={"metadata": {"path": str(out_dir)}}).execute()
        nbf.write(nb, out_dir / f"{fname}.ipynb")
        print("built", name)
