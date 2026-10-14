"""House chart style: one typeface, restrained palette, one colour per segment.

All figures in the notebooks, README and paper are drawn through this module so the
project reads as a single piece of work.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

INK = "#1B1F24"        # primary text / strategy line
MUTED = "#6B7280"      # secondary text, benchmarks
GRID = "#E5E7EB"
PAPER = "#FFFFFF"
ACCENT = "#1B1F24"     # strategy lines are drawn in ink; segments carry the colour
NEGATIVE = "#B91C1C"
POSITIVE = "#15803D"

# Validated with the dataviz palette checker (all pairs, light surface): lightness band,
# chroma floor, colour-blind separation (worst dE 10.4) and contrast all pass.
SEGMENT_COLORS = {
    "dry_bulk": "#D2770F",    # amber / ore
    "tankers": "#2A78D6",     # blue / crude
    "containers": "#1BA57A",  # green / box
    "gas": "#B04A9C",         # magenta / LNG
}

REGIMES = [  # shaded on long-history charts
    ("2015-11-01", "2016-06-30", "2016 dry bulk trough"),
    ("2020-02-15", "2020-05-31", "COVID shock"),
    ("2022-02-24", "2022-12-31", "Russia sanctions / tanker rerouting"),
    ("2023-11-15", "2024-12-31", "Red Sea disruption"),
]


def apply() -> None:
    mpl.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "savefig.facecolor": PAPER,
            "figure.dpi": 110,
            "savefig.dpi": 200,
            "savefig.bbox": "tight",
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.titlepad": 24,
            "axes.labelcolor": MUTED,
            "axes.labelsize": 9,
            "axes.edgecolor": GRID,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "ytick.left": False,
            "legend.frameon": False,
            "legend.fontsize": 8.5,
            "lines.linewidth": 1.6,
            "text.color": INK,
            "text.parse_math": False,
        }
    )


def subtitle(ax, text: str) -> None:
    """Grey one-line subtitle under a left-aligned bold title."""
    ax.text(0, 1.015, text, transform=ax.transAxes, fontsize=9, color=MUTED, va="bottom")


def source(fig, text: str) -> None:
    fig.text(0.01, -0.02, text, fontsize=7.5, color=MUTED, ha="left", va="top")


def shade_regimes(ax, labels: bool = True, alpha: float = 0.07) -> None:
    import pandas as pd

    ymax = ax.get_ylim()[1]
    for start, end, label in REGIMES:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=INK, alpha=alpha, lw=0)
        if labels:
            ax.text(pd.Timestamp(start), ymax, " " + label, fontsize=7, color=MUTED,
                    va="top", ha="left", rotation=90)


def new(figsize=(10, 4.2)):
    apply()
    return plt.subplots(figsize=figsize)


def log_axis(ax, fmt="{:,.0f}") -> None:
    """Log y-axis with plain tick labels (mathtext is off so '$' renders literally)."""
    import matplotlib.ticker as mt

    ax.set_yscale("log")
    ax.yaxis.set_major_locator(mt.LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: fmt.format(v)))
    ax.yaxis.set_minor_formatter(mt.NullFormatter())
