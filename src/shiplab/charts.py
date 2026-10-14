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
    ax.set_yscale("log")
    for s, lab, col in [(all_names, "Every name, including the dead", style.INK),
                        (surv, "Only today's survivors", style.MUTED)]:
        ax.text(s.index[-1] + pd.Timedelta(days=40), s.iloc[-1],
                f"{lab}\n{cagr(s):+.1%} a year", fontsize=8, color=col, va="center")
    ax.set_xlim(right=ax.get_xlim()[1] + 900)
    gap = cagr(surv) - cagr(all_names)
    ax.set_title("Survivorship: backtesting on today's tickers flatters shipping")
    style.subtitle(ax, f"Equal-weight daily-rebalanced total return, USD, log scale. "
                       f"Survivor-only history overstates the return by {gap:.1%} a year.")
    return fig, gap
