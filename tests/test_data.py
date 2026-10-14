import numpy as np
import pandas as pd

from shiplab import prices
from shiplab.panel import repair_bad_prints
from shiplab.universe import load_register


def test_total_return_includes_liquidating_distribution():
    idx = pd.date_range("2026-04-27", periods=3, freq="B")
    df = pd.DataFrame({"close": [131.8, 131.8, 4.324], "volume": [1, 1, 1],
                       "dividend": [0, 0, 131.44307], "split": 1.0,
                       "close_is_split_adjusted": True}, index=idx)
    r = prices.total_return(df)
    assert abs(r.iloc[-1] - ((4.324 + 131.44307) / 131.8 - 1)) < 1e-12


def test_split_handled_for_raw_closes():
    idx = pd.date_range("2020-01-01", periods=2, freq="B")
    df = pd.DataFrame({"close": [10.0, 50.0], "volume": [1, 1], "dividend": [0, 0],
                       "split": [1.0, 0.2], "close_is_split_adjusted": False}, index=idx)
    # 1-for-5 reverse split: 10 -> 50 is a 0% return
    assert abs(prices.total_return(df).iloc[-1]) < 1e-12


def test_zero_volume_days_are_not_returns():
    idx = pd.date_range("2020-01-01", periods=3, freq="B")
    df = pd.DataFrame({"close": [10.0, 10.0, 11.0], "volume": [5, 0, 5], "dividend": 0.0,
                       "split": 1.0, "close_is_split_adjusted": True}, index=idx)
    r = prices.total_return(df)
    assert idx[1] not in r.index and abs(r.loc[idx[2]] - 0.1) < 1e-12


def test_bad_print_repair_preserves_two_day_return():
    r = pd.DataFrame({"X": [0.01, -0.4, 0.7, 0.0]})
    fixed, log = repair_bad_prints(r)
    assert len(log) == 1 and fixed.iloc[1, 0] == 0.0
    assert np.isclose(fixed.iloc[2, 0], 0.6 * 1.7 - 1)


def test_register_integrity():
    reg = load_register()
    assert reg["id"].is_unique
    inc = reg[reg["include"]]
    assert inc["symbol"].notna().all()
    closed = inc.dropna(subset=["end"])
    assert (closed["end"] > closed["start"]).all()
