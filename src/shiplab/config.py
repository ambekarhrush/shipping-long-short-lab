"""Project paths and study-wide constants."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
REFERENCE = DATA / "reference"
CACHE = DATA / "cache"
FIGURES = ROOT / "figures"

# Study calendar. Prices from WARMUP_START feed look-back windows only.
WARMUP_START = "2010-01-01"
STUDY_START = "2011-01-01"
DEVELOPMENT_END = "2020-12-31"   # parameters designed on this window
VALIDATION_END = "2022-12-31"    # walk-forward validation window
HOLDOUT_START = "2023-01-01"     # sealed: run once, at the end

SEGMENTS = ["dry_bulk", "tankers", "containers", "gas"]
SEGMENT_LABELS = {
    "dry_bulk": "Dry bulk",
    "tankers": "Tankers",
    "containers": "Containers",
    "gas": "Gas carriers",
}
