"""Chart builders shared by the notebooks, README and paper."""

from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from . import style
from .config import FIGURES, SEGMENT_LABELS, SEGMENTS, STUDY_START

EXIT_MARKERS = {
    "merger_stock": ("o", "Merged"),
    "take_private": ("s", "Taken private"),
    "bankruptcy": ("X", "Bankrupt"),
    "distress": ("X", "Bankrupt"),
    "asset_sale": ("D", "Sold fleet"),
    "reclassified": ("^", "Left segment"),
}


def save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{name}.png")


def universe_timeline(reg: pd.DataFrame, panel_index: pd.DatetimeIndex, first_data: pd.Series):
    """One bar per company, coloured by segment; hatched grey where no free data exists."""
    style.apply()
    end_default = panel_index[-1]
    study0 = pd.Timestamp(STUDY_START)
    reg = reg[reg["segment"].isin(SEGMENTS)].copy()
    reg["s"] = reg["start"].fillna(study0).clip(lower=study0)
    reg["e"] = reg["end"].fillna(end_default)
    reg = reg[reg["e"] > study0]
    reg["seg_order"] = reg["segment"].map({s: k for k, s in enumerate(SEGMENTS)})
    reg = reg.sort_values(["seg_order", "s", "e"], ascending=[True, True, True])
    n = len(reg)
    fig, ax = plt.subplots(figsize=(11, 0.21 * n + 1.6))
    ax.grid(False)
    for k, row in enumerate(reg.itertuples()):
        y = n - 1 - k
        color = style.SEGMENT_COLORS[row.segment]
        if row.include:
            s = max(row.s, first_data.get(row.id, row.s)) if row.id in first_data else row.s
            ax.barh(y, row.e - s, left=s, height=0.62, color=color, lw=0)
        else:
            ax.barh(y, row.e - row.s, left=row.s, height=0.62, color="white",
                    edgecolor=style.MUTED, hatch="////", lw=0.6)
        if pd.notna(row.end) and row.exit_type in EXIT_MARKERS:
            m, _ = EXIT_MARKERS[row.exit_type]
            ax.plot(row.e, y, marker=m, ms=5.5, color=style.INK, mec="white", mew=0.8)
        if pd.notna(row.deal_announced) and row.include:
            ax.plot(row.deal_announced, y, marker="|", ms=9, color=style.INK, mew=1.4)
        label = row.id.replace("_OLD", "").replace("_OSL", "").replace("_T", "").replace("_C", "")
        ax.text(study0 - pd.Timedelta(days=40), y, label, ha="right", va="center",
                fontsize=7.2, color=style.INK if row.include else style.MUTED)
    ax.set_yticks([])
    ax.set_ylim(-1, n)
    ax.set_xlim(study0 - pd.Timedelta(days=30), end_default + pd.Timedelta(days=60))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", which="both", bottom=False)
    for x in pd.date_range("2012", "2026", freq="2YS"):
        ax.axvline(x, color=style.GRID, lw=0.7, zorder=0)
    handles = [Patch(color=style.SEGMENT_COLORS[s], label=SEGMENT_LABELS[s]) for s in SEGMENTS]
    handles.append(Patch(facecolor="white", edgecolor=style.MUTED, hatch="////",
                         label="No free price history (documented gap)"))
    for key in ["merger_stock", "take_private", "bankruptcy", "asset_sale", "reclassified"]:
        m, lab = EXIT_MARKERS[key]
        handles.append(plt.Line2D([], [], marker=m, ls="", color=style.INK, label=lab, ms=5.5))
    handles.append(plt.Line2D([], [], marker="|", ls="", color=style.INK, ms=9, mew=1.4,
                              label="Takeover public (signals frozen)"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.03 - 1.0 / n),
              ncol=5, fontsize=7.8)
    ax.set_title("Who was in the universe, and how they left")
    style.subtitle(ax, f"{int(reg['include'].sum())} tradable companies across four segments, "
                   f"{int((reg['end'].notna() & reg['include']).sum())} of which left before "
                   "today. Dead names stay in the backtest.")
    return fig


def breadth(investable: pd.DataFrame, reg: pd.DataFrame):
    """Investable names per segment over time (monthly), small multiples."""
    style.apply()
    seg = reg.set_index("id")["segment"]
    m = investable.resample("ME").last()
    fig, axes = plt.subplots(1, 4, figsize=(11, 2.9), sharey=True)
    for ax, s in zip(axes, SEGMENTS):
        cols = [c for c in m.columns if seg.get(c) == s]
        cnt = m[cols].sum(axis=1)
        ax.fill_between(cnt.index, 0, cnt.values, step="post",
                        color=style.SEGMENT_COLORS[s], alpha=0.85, lw=0)
        ax.axhline(4, color=style.INK, lw=0.8, ls=(0, (3, 2)))
        ax.set_title(SEGMENT_LABELS[s], fontsize=10)
        ax.xaxis.set_major_locator(mdates.YearLocator(5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        last = int(cnt.iloc[-1])
        ax.text(cnt.index[-1], last + 0.4, str(last), fontsize=8, ha="right", color=style.INK)
    axes[0].text(m.index[0], 4.4, "4 names: minimum for a\nsegment-neutral book", fontsize=7,
                 color=style.MUTED, va="bottom")
    fig.suptitle("Investable names per segment", x=0.01, ha="left", fontweight="bold", y=1.04)
    fig.text(0.01, 0.97, "In the universe, 60-day median traded value at least $1m, price at "
             "least $2, no takeover pending. Month-end counts.", fontsize=9, color=style.MUTED)
    return fig


def fx_glitch(yahoo_nok: pd.Series, fred_nok: pd.Series, start="2020-02-20", end="2020-04-20"):
    style.apply()
    fig, ax = plt.subplots(figsize=(8, 3.2))
    y = yahoo_nok.loc[start:end]
    f = fred_nok.loc[start:end]
    ax.plot(f.index, f.values, color=style.INK, label="Federal Reserve H.10 (used)")
    ax.plot(y.index, y.values, color=style.MUTED, lw=1.1, ls=(0, (3, 2)),
            label="Yahoo NOK=X (rejected)")
    bad = y.idxmin()
    ax.annotate(f"Yahoo prints {y.min():.2f} NOK/USD on {bad:%d %b %Y}\n"
                f"Fed: {f.get(bad, np.nan):.2f}. Every Oslo stock would show a\n"
                "+45% day followed by a -35% day.", xy=(bad, y.min()),
                xytext=(bad + pd.Timedelta(days=6), y.min() + 0.3), fontsize=8,
                arrowprops=dict(arrowstyle="-", color=style.MUTED, lw=0.8))
    ax.set_ylabel("NOK per USD")
    ax.legend(loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_title("One bad FX print would have fabricated a market-wide event")
    style.subtitle(ax, "USD/NOK, February to April 2020")
    return fig


def adv_by_segment(dollar_volume: pd.DataFrame, member: pd.DataFrame, reg: pd.DataFrame):
    style.apply()
    seg = reg.set_index("id")["segment"]
    adv = dollar_volume.where(member).rolling(63, min_periods=20).median()
    fig, ax = plt.subplots(figsize=(10, 3.6))
    for s in SEGMENTS:
        cols = [c for c in adv.columns if seg.get(c) == s]
        med = adv[cols].median(axis=1).resample("ME").last() / 1e6
        ax.plot(med.index, med.values, color=style.SEGMENT_COLORS[s], lw=1.8)
        ax.text(med.index[-1] + pd.Timedelta(days=40), med.iloc[-1], SEGMENT_LABELS[s],
                color=style.INK, fontsize=8, va="center")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}m" if v >= 1
                                                   else f"${v:.1f}m"))
    ax.set_xlim(right=ax.get_xlim()[1] + 500)
    ax.set_title("Liquidity: the typical stock trades a few million dollars a day")
    style.subtitle(ax, "Median across names of the 3-month median daily traded value, USD, "
                   "log scale")
    return fig


def survivorship(total_return: pd.DataFrame, reg: pd.DataFrame):
    """Equal-weight index of every name vs only the names still listed today."""
    style.apply()
    alive = reg.loc[reg["end"].isna() & reg["include"], "id"]
    r = total_return.loc[STUDY_START:]
    all_names = (1 + r.mean(axis=1).fillna(0)).cumprod()
    surv = (1 + r[[c for c in r.columns if c in set(alive)]].mean(axis=1).fillna(0)).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = lambda s: s.iloc[-1] ** (1 / yrs) - 1  # noqa: E731
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.plot(all_names.index, all_names.values, color=style.INK, lw=1.8)
    ax.plot(surv.index, surv.values, color=style.MUTED, lw=1.4, ls=(0, (4, 2)))
    style.log_axis(ax, "{:.1f}x")
    for s, lab, col in [(all_names, "Every name, including the dead", style.INK),
                        (surv, "Only today's survivors", style.MUTED)]:
        off = 1.06 if col == style.INK else 0.94
        ax.text(s.index[-1] + pd.Timedelta(days=40), s.iloc[-1] * off,
                f"{lab}: {cagr(s):+.1%} a year", fontsize=8, color=col, va="center")
    ax.set_xlim(right=ax.get_xlim()[1] + 900)
    gap = cagr(surv) - cagr(all_names)
    if abs(gap) < 0.002:
        msg = "changes the return by less than 0.2% a year"
    else:
        msg = f"{'overstates' if gap > 0 else 'understates'} the return by {abs(gap):.1%} a year"
    ax.set_title("Survivorship in shipping cuts both ways")
    style.subtitle(ax, f"Equal-weight total return, USD, log scale. Dropping dead names {msg}: most "
                       "exits were takeovers at a premium, and the bankruptcies have no free data.")
    return fig, gap


# ---------------------------------------------------------------- results charts
PERIOD_SHADES = [("2015-01-01", "2020-12-31", "Walk-forward"), ("2021-01-01", "2022-12-31", "Validation"),
                 ("2023-01-01", "2026-12-31", "Sealed holdout")]


def equity_curve(strategy: pd.Series, benchmarks: dict, start="2015-01-01"):
    """Cumulative return on a log scale, with the research periods shaded."""
    style.apply()
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(10.5, 5.6), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1.1], "hspace": 0.08})
    s = strategy.loc[start:].fillna(0)
    eq = (1 + s).cumprod()
    for (a, b, lab), alpha in zip(PERIOD_SHADES, (0.0, 0.05, 0.10)):
        for x in (ax, ax2):
            x.axvspan(pd.Timestamp(a), min(pd.Timestamp(b), s.index[-1]), color=style.INK, alpha=alpha, lw=0)
        ax.text(pd.Timestamp(a) + pd.Timedelta(days=30), 0.97, lab, transform=ax.get_xaxis_transform(),
                fontsize=8, color=style.MUTED, va="top")
    greys = [style.MUTED, "#9CA3AF", "#C4C8CE"]
    ends = []
    for (name, b), col in zip(benchmarks.items(), greys):
        be = (1 + b.reindex(s.index).fillna(0)).cumprod()
        ax.plot(be.index, be.values, color=col, lw=1.1)
        y = be.iloc[-1]
        for e in ends:                       # keep end labels apart on the log scale
            if abs(np.log(y / e)) < 0.08:
                y = e * (0.9 if y <= e else 1.1)
        ends.append(y)
        ax.text(be.index[-1] + pd.Timedelta(days=30), y, name, fontsize=8, color=style.MUTED, va="center")
    ax.plot(eq.index, eq.values, color=style.INK, lw=2.0)
    ax.text(eq.index[-1] + pd.Timedelta(days=30), eq.iloc[-1], "Strategy", fontsize=8.5,
            color=style.INK, va="center", fontweight="bold")
    style.log_axis(ax, "{:.1f}x")
    ax.set_xlim(right=s.index[-1] + pd.Timedelta(days=500))
    dd = eq / eq.cummax() - 1
    ax2.fill_between(dd.index, dd.values * 100, 0, color=style.NEGATIVE, alpha=0.35, lw=0)
    ax2.set_ylabel("Drawdown %")
    ax.set_title("Market-neutral shipping long/short vs the market it trades")
    style.subtitle(ax, "Growth of $1, log scale, net of trading costs, borrow and the SPY hedge; "
                       "USD 10m reference fund")
    return fig


def capacity(cap: pd.DataFrame):
    style.apply()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.4))
    a1.plot(range(len(cap)), cap["sharpe"], marker="o", color=style.INK)
    a1.set_xticks(range(len(cap)), [f"{x:g}" for x in cap["aum_musd"]])
    a1.set_xlabel("Fund size, USD m")
    a1.set_title("Sharpe ratio", fontsize=10)
    a2.bar(range(len(cap)), cap["alpha_musd_per_year"], color=style.SEGMENT_COLORS["tankers"], width=0.6)
    a2.set_xticks(range(len(cap)), [f"{x:g}" for x in cap["aum_musd"]])
    a2.set_xlabel("Fund size, USD m")
    a2.set_title("Return in USD m per year", fontsize=10)
    fig.subplots_adjust(top=0.78, wspace=0.3)
    fig.suptitle("Capacity: the edge is real but small", x=0.01, ha="left", fontweight="bold", y=1.0)
    fig.text(0.01, 0.91, "Walk-forward 2014-2022. Positions capped at 10% of a stock's daily traded value.",
             fontsize=9, color=style.MUTED)
    return fig


def lead_lag(ll: pd.DataFrame):
    style.apply()
    fig, ax = plt.subplots(figsize=(9, 3.4))
    for seg in ll.columns:
        ax.plot(ll.index, ll[seg], marker="o", ms=4, color=style.SEGMENT_COLORS[seg], lw=1.5)
        ax.text(ll.index[-1] + 0.3, ll[seg].iloc[-1], SEGMENT_LABELS[seg], fontsize=8, va="center")
    ax.axvline(0, color=style.MUTED, lw=0.8)
    ax.axhline(0, color=style.MUTED, lw=0.8)
    ax.set_xlabel("Weeks by which equities lead freight (negative: freight leads equities)")
    ax.set_ylabel("Correlation of weekly changes")
    ax.set_xlim(ll.index.min() - 0.5, ll.index.max() + 2.5)
    ax.set_title("Public freight data is priced within the week")
    style.subtitle(ax, "Segment equity basket vs its Baltic freight index, weekly, 2011-2022")
    return fig


def attribution_bars(att: pd.DataFrame, years: float):
    style.apply()
    a = (att.sum() / years * 100)
    segs = [s for s in SEGMENTS if f"{s}|long" in a]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    x = np.arange(len(segs))
    ax.bar(x - 0.2, [a[f"{s}|long"] for s in segs], 0.38, color=[style.SEGMENT_COLORS[s] for s in segs])
    ax.bar(x + 0.2, [a[f"{s}|short"] for s in segs], 0.38, color=[style.SEGMENT_COLORS[s] for s in segs],
           alpha=0.45, hatch="////", edgecolor="white")
    ax.set_xticks(x, [SEGMENT_LABELS[s] for s in segs])
    ax.axhline(0, color=style.INK, lw=0.8)
    ax.set_ylabel("% per year")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=style.MUTED, label="Long book"),
                       Patch(facecolor=style.MUTED, alpha=0.45, hatch="////", edgecolor="white", label="Short book")],
              loc="upper left")
    ax.set_title("Where the return came from")
    style.subtitle(ax, "Contribution to annual return by segment and side, 2014 to date")
    return fig


def stress_bars(stress: pd.DataFrame):
    style.apply()
    p = stress.pivot(index="window", columns="series", values="total_return") * 100
    order = ["2016 dry bulk trough", "COVID shock", "2022 Russia sanctions", "Red Sea disruption", "2026 Hormuz crisis"]
    p = p.reindex([o for o in order if o in p.index])
    fig, ax = plt.subplots(figsize=(10, 3.6))
    x = np.arange(len(p))
    cols = {"Strategy": style.INK, "EW shipping basket": style.SEGMENT_COLORS["tankers"], "SPY": "#C4C8CE"}
    for k, (name, col) in enumerate(cols.items()):
        if name in p:
            ax.bar(x + (k - 1) * 0.26, p[name], 0.24, color=col, label=name)
    ax.set_xticks(x, p.index, fontsize=8.5)
    ax.axhline(0, color=style.INK, lw=0.8)
    ax.set_ylabel("Total return over window, %")
    ax.legend(loc="upper left", ncol=3)
    ax.set_title("Stress windows")
    style.subtitle(ax, "Strategy vs equal-weight shipping basket and S&P 500 over each episode")
    return fig


def trials_histogram(trials: pd.DataFrame, chosen_sharpe: float, dsr: float):
    style.apply()
    t = trials[trials.tag == "research"]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.hist(t["sharpe"].dropna(), bins=15, color="#C4C8CE", edgecolor="white")
    ax.axvline(chosen_sharpe, color=style.INK, lw=1.8)
    ax.text(chosen_sharpe, ax.get_ylim()[1] * 0.92, f"  Holdout Sharpe {chosen_sharpe:.2f}\n  "
            f"deflated-Sharpe probability {dsr:.2f}", fontsize=8, va="top")
    ax.set_xlabel("Annualised Sharpe of each research variant")
    ax.set_ylabel("Variants")
    ax.set_title(f"Every variant tried ({len(t)}), not just the winner")
    style.subtitle(ax, "From the automatic trials ledger; the deflated Sharpe corrects for this search")
    return fig


def freight_vs_equity(fr: pd.DataFrame, baskets: pd.DataFrame, start="2011-01-01"):
    """Fifteen years of context: segment equity baskets against their freight index."""
    style.apply()
    pairs = [("dry_bulk", "BDI"), ("tankers", "BDTI"), ("containers", None), ("gas", "BLPG")]
    fig, axes = plt.subplots(2, 2, figsize=(11, 5.6), sharex=True)
    for ax, (seg, sym) in zip(axes.ravel(), pairs):
        b = (1 + baskets[seg].loc[start:].fillna(0)).cumprod()
        ax.plot(b.index, b / b.iloc[0] * 100, color=style.SEGMENT_COLORS[seg], lw=1.6, label="Equity basket")
        if sym and sym in fr:
            f = fr[sym].loc[start:].dropna()
            ax.plot(f.index, f / f.iloc[0] * 100 * (b.iloc[0] / b.iloc[0]), color=style.MUTED, lw=1.0, label=f"{sym} index")
        style.log_axis(ax)
        ax.set_title(SEGMENT_LABELS[seg], fontsize=10)
        style.shade_regimes(ax, labels=False)
    axes[0, 0].legend(loc="upper left")
    fig.suptitle("Fifteen years of shipping: equities and freight, rebased to 100", x=0.01, ha="left",
                 fontweight="bold", y=1.02)
    fig.text(0.01, 0.97, "Equal-weight investable basket per segment (total return, USD) vs its Baltic index; "
             "shaded: 2016 trough, COVID, 2022 sanctions, Red Sea. Containers: no free charter index.",
             fontsize=8.5, color=style.MUTED)
    fig.tight_layout()
    return fig


def dispersion(tr: pd.DataFrame, inv: pd.DataFrame, seg: pd.Series):
    """Within-segment spread of 12-month returns: the raw material of stock selection."""
    style.apply()
    r12 = (1 + tr.fillna(0)).rolling(252).apply(np.prod, raw=True) - 1
    r12 = r12.where(inv).resample("ME").last()
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for s in SEGMENTS:
        cols = [c for c in r12.columns if seg.get(c) == s]
        q = r12[cols]
        n = q.notna().sum(axis=1)
        spread = (q.quantile(0.75, axis=1) - q.quantile(0.25, axis=1)).where(n >= 4) * 100
        ax.plot(spread.index, spread.values, color=style.SEGMENT_COLORS[s], lw=1.4)
        last = spread.dropna()
        if len(last):
            ax.text(last.index[-1] + pd.Timedelta(days=40), last.iloc[-1], SEGMENT_LABELS[s], fontsize=8, va="center")
    ax.set_xlim(right=ax.get_xlim()[1] + 500)
    ax.set_ylim(0, 200)
    ax.text(0.99, 0.97, "axis capped at 200; 2021 container spread peaked near 700", transform=ax.transAxes,
            ha="right", va="top", fontsize=7.5, color=style.MUTED)
    ax.set_ylabel("Percentage points")
    ax.set_title("Same freight market, very different outcomes")
    style.subtitle(ax, "Gap between the 75th and 25th percentile 12-month return within each segment "
                       "(months with 4+ investable names)")
    return fig


def portwatch_vs_freight(pwf: pd.DataFrame):
    """Aggregate AIS (PortWatch chokepoints) vs freight: same month and next month."""
    style.apply()
    fig, ax = plt.subplots(figsize=(9, 3.2))
    y = np.arange(len(pwf))
    ax.barh(y + 0.18, pwf["corr_same_4w"], 0.34, color="#C4C8CE", label="Same four weeks")
    ax.barh(y - 0.18, pwf["corr_next_4w"], 0.34, color=style.INK, label="Next four weeks")
    ax.set_yticks(y, [f"{s} vs {f}" for s, f in zip(pwf["signal"], pwf["freight"])], fontsize=8.5)
    ax.axvline(0, color=style.INK, lw=0.8)
    ax.set_xlim(-0.3, 0.3)
    ax.grid(axis="x", color=style.GRID); ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    ax.set_xlabel("Correlation with change in freight index")
    ax.set_title("Aggregate ship-tracking data does not predict freight either")
    style.subtitle(ax, "IMF PortWatch chokepoint transits (2019-2026), four-week changes vs Baltic index")
    return fig


def fleet_register(reg: pd.DataFrame):
    """Ships and deadweight per listed owner in the FleetWatch register."""
    style.apply()
    op = reg[~reg["newbuild"]]
    g = op.groupby(["segment", "universe_id"]).agg(ships=("vessel", "size"), dwt=("dwt", "sum")).reset_index()
    g = g.sort_values(["segment", "dwt"])
    fig, ax = plt.subplots(figsize=(10, 5.2))
    y = np.arange(len(g))
    ax.barh(y, g["dwt"] / 1e6, color=[style.SEGMENT_COLORS[s] for s in g["segment"]], height=0.7)
    for yy, (n, d) in enumerate(zip(g["ships"], g["dwt"] / 1e6)):
        ax.text(d + 0.2, yy, f"{n} ships", va="center", fontsize=7.5, color=style.MUTED)
    ax.set_yticks(y, g["universe_id"], fontsize=8.5)
    ax.grid(axis="x", color=style.GRID); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Fleet deadweight, million tonnes")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=style.SEGMENT_COLORS[s], label=SEGMENT_LABELS[s]) for s in ("dry_bulk", "tankers")],
              loc="lower right")
    ax.set_title(f"FleetWatch register: {len(op):,} ships of {g['universe_id'].nunique()} listed owners")
    style.subtitle(ax, "Operating fleets extracted from each company's latest SEC annual report or fleet employment table")
    return fig
