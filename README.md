# Where is the edge in listed shipping?

**Four connected research projects on 54 New York- and Oslo-listed shipping companies,
2011-2026: clean data, a fast market, a small public-data alpha, and a live ship-level record
built to find what the market sees late.**

![Strategy vs S&P 500 and the shipping basket](figures/eq_curve.png)

## The argument in three findings

1. **Public freight data is priced within the week.** Shipping equities and the Baltic indices
   move together; neither freight nor aggregate ship-tracking data predicts next month.
2. **So public-data stock selection earns little.** A market-neutral long/short book earned a
   Sharpe of 0.42 in a sealed, pre-registered 2023-2026 holdout (beta -0.01), capped at roughly
   a USD 25m fund, and not significant after correcting for 27 logged trials.
3. **So the edge, if any, is in the ships.** FleetWatch maps ~1,000 ships to their 21 listed
   owners from the companies' own filings and records them hourly, before each company reports.

## The projects

| | Project | Question | Answer |
|---|---|---|---|
| 01 | [**Data foundation**](01-data-foundation) | Can free data support an honest shipping backtest? | Yes, after fixing errors that would fake results: bad FX prints, missed distributions, recycled tickers. 73-company point-in-time universe. |
| 02 | [**Freight priced by Friday**](02-freight-priced-by-friday) | Do freight indices or aggregate AIS predict shipping stocks? | No. Same-week correlation 0.33-0.37; no month-ahead signal. |
| 03 | [**Market-neutral long/short**](03-market-neutral-long-short) | Is there stock-selection alpha from public data? | Small and neutral: holdout Sharpe 0.42, beta about zero, capacity about USD 25m, deflated-Sharpe probability 0.31. |
| 04 | [**FleetWatch**](04-fleetwatch) | Can ship-level tracking see what the market prices late? | Live since October 2026; first scored season Q4 2026. Historical US-waters test pre-registered. |

**Read in five minutes:** the [two-page note](paper/research_note.pdf). **Full paper:**
[*Priced by Friday*](paper/shipping_long_short.pdf) (8 pages).

## How the work protects itself

Point-in-time universe with dead companies kept in · total returns rebuilt from raw prices ·
walk-forward parameter choice · every variant logged automatically ·
[holdout pre-registered in git](docs/PREREGISTRATION.md) before a single run · deflated Sharpe ·
costs, borrow, liquidity caps and a market hedge in every number · live estimates committed
before results.

## Run it

```bash
uv sync --frozen --extra dev
echo "TIINGO_API_KEY=..." > .env            # free key, for delisted US names
uv run python scripts/pull_prices.py        # freight file: see docs/DATA.md
uv run python scripts/run_research.py --holdout
uv run python scripts/build_notebooks.py
uv run pytest -q
```

Shared code lives in [`src/shiplab`](src/shiplab); each project folder holds its own README and
notebooks.

---

*Independent research project by Hrushikesh Ambekar. Not affiliated with, endorsed by or
produced for any current, previous or future employer of the author. Public data only. Not
investment advice.*
