# 03 · Market-neutral long/short

**Question.** Is there stock-selection alpha in listed shipping using public data only?

**Answer.** A small, genuinely market-neutral one, which holds out of sample but is not
statistically distinguishable from luck after correcting for the search, and which caps out
at roughly a USD 25m fund.

![Strategy vs S&P 500 and the shipping basket](../figures/eq_curve.png)

| USD 10m reference fund, net of costs | Sharpe | Return p.a. | Vol | Max DD | Beta |
|---|---|---|---|---|---|
| Walk-forward 2014-2020 | 0.70 | 3.6% | 5.2% | -7.5% | 0.03 |
| Validation 2021-2022 | 0.61 | 3.3% | 5.5% | -5.1% | 0.01 |
| **Sealed holdout 2023 - Oct 2026** | **0.42** | 2.1% | 5.3% | -7.2% | -0.01 |

**What worked:** cheapness (book-to-market) within a segment; fading moves out of line with a
stock's freight sensitivity. **What did not:** pairs; freight timing; balance-sheet strength on
its own (it works in dry bulk, reverses among container owners). A pre-registered hypothesis
that strong balance sheets pay only in falling freight markets was rejected and left rejected.

**How the result was protected from overfitting**
* Parameters chosen each year on prior data only (walk-forward).
* Every variant written automatically to [`trials.csv`](../data/results/trials.csv) (27 research variants).
* Holdout sealed in code; configuration committed before the single run: [`PREREGISTRATION.md`](../docs/PREREGISTRATION.md).
* Deflated Sharpe probability on the holdout: 0.31 (0.95 would indicate skill).

| Capacity | USD 2m | 10m | 25m | 50m | 100m |
|---|---|---|---|---|---|
| Sharpe | 0.79 | 0.68 | 0.60 | 0.46 | 0.38 |
| USD m per year | 0.11 | 0.35 | 0.62 | 0.71 | 0.79 |

Stress: +4.4% in the 2016 dry bulk trough (basket -36%), +5.3% through the Red Sea disruption,
-5.0% in the 2026 Hormuz crisis.

| | |
|---|---|
| Summary notebook | [`notebooks/00_summary.ipynb`](notebooks/00_summary.ipynb) |
| Detail | signals, three sleeves, portfolio and risk, robustness, stress windows (`notebooks/01-07`) |
| Reproduce | `uv run python scripts/run_research.py --holdout` |

**Previous:** [← 02 · Freight priced by Friday](../02-freight-priced-by-friday) · **Next:** [04 · FleetWatch →](../04-fleetwatch)
