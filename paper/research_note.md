---
title: "Shipping long/short: research note"
subtitle: "Public data is priced by Friday. The edge is in the ships."
author: "Hrushikesh Ambekar"
date: "October 2026"
---

*Independent research project. Not affiliated with, endorsed by or produced for any current,
previous or future employer of the author. Public data only. Not investment advice.*

## What was tested

A market-neutral long/short book in 54 New York- and Oslo-listed shipping companies (dry bulk,
tankers, containers, gas), 2011 to October 2026, with merged, bankrupt and reclassified
companies kept in. Three segment-neutral sleeves: pairs; factor ranks (book-to-market,
balance-sheet strength, freight-beta momentum); and fading moves out of line with each stock's
freight sensitivity. Costs, borrow, dividends on shorts, NOK currency, liquidity caps and a SPY
beta hedge are included. Parameters were chosen year by year on past data; every variant was
logged; the 2023-2026 holdout was pre-registered in git and run once.

## Results

[Figure 4]

| Period | Sharpe | Return p.a. | Volatility | Max drawdown | Beta |
|---|---|---|---|---|---|
| Walk-forward 2014-2020 | 0.70 | 3.6% | 5.2% | -7.5% | 0.03 |
| Validation 2021-2022 | 0.61 | 3.3% | 5.5% | -5.1% | 0.01 |
| Sealed holdout 2023 - Oct 2026 | 0.42 | 2.1% | 5.3% | -7.2% | -0.01 |

## Findings

1. **Freight is priced within the week.** Equity baskets and Baltic indices move together
   (weekly correlation about 0.35); freight does not predict next month's dry bulk returns.
2. **Within-segment cheapness and freight-unexplained dislocations earn a small, market-neutral
   return.** Balance-sheet strength works in dry bulk and reverses among container owners; a
   pre-registered "balance sheet as option strike" hypothesis was rejected.
3. **Capacity binds.** Sharpe about 0.8 at USD 2m, 0.6 at USD 25m, 0.45 at USD 50m; dollar alpha
   plateaus below USD 1m a year.
4. **Not significant after the search.** Deflated-Sharpe probability 0.31 over 27 logged trials.
5. **Stress:** +4.4% in the 2016 trough (basket -36%), +5.3% through the Red Sea disruption,
   -5.0% in the 2026 Hormuz crisis.
6. **Results-day text is read slowly.** Parsing 758 results releases: when next-quarter bookings
   run above the rate just earned, the stock beat its segment by about 3% over the next month
   (rank correlation 0.26, t 2.2, 66 releases; not pre-registered). Port and chokepoint data
   do not improve freight nowcasts; a pre-registered US-waters idle-ship test was null.

## Implication and next step

If public freight data is priced within days, a durable edge must come from company-specific
operating information that reaches the market late. FleetWatch maps about 1,000 ships to their
21 listed owners from the companies' own filings and tracks them hourly via AIS: idle share,
laden share and regional exposure by owner. Every estimate is committed to the public repository
before the company reports; the first scored season is Q4 2026 (February 2027).

## Limitations

Small, illiquid universe; book value stands in for net asset value; borrow modelled, not
observed; several bankruptcies and four recycled-ticker mergers lack free price history; Oslo-
only names lack machine-readable fundamentals; terrestrial AIS loses ships mid-ocean.
