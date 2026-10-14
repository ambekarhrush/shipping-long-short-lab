# Holdout pre-registration

Committed **before** the sealed holdout window was run. The commit timestamp of this file in
git history is the evidence that the configuration below was fixed in advance.

| Item | Fixed value |
|---|---|
| Holdout window | 2023-01-03 to 2026-10-13 (last available close at registration) |
| Sleeves | Factor long/short + equity-vs-freight residual. **Pairs excluded**: walk-forward Sharpe through 2022 was below zero (-0.04). |
| Factor sleeve | Within-segment ranks of book-to-market and freight-beta momentum (63-day), equal weights; long top third, short bottom third; inverse-volatility legs; dollar-neutral per segment; weekly (Wednesday) rebalance |
| Residual sleeve | 252-day rolling regression of each stock on its segment freight index and SPY; fade the 10-day cumulative residual, z-score entry 0.75, segment-neutral; weekly rebalance |
| Parameter choice | The walk-forward picks for 2022 (chosen on 2011-2021 data), frozen for the whole holdout |
| Risk | 6% ex-ante vol per sleeve; name cap 7.5% NAV; gross cap 250%; 10% of 60-day median ADV per name; SPY beta hedge; drawdown brake at -15% (release -7.5%) |
| Costs | Half-spread 5-60 bp by ADV tier + square-root impact; borrow 0.5%-15% p.a. by ADV tier; dividends on shorts paid; NOK unhedged |
| Reference AUM | USD 10m (capacity analysis separately) |
| Universe and screens | Point-in-time register (54 tradable names); ADV >= $1m, price >= $2, no pending takeover |
| Reported | Annual return, volatility, Sharpe, max drawdown, monthly hit rate, beta to SPY; versus the equal-weight shipping basket, segment baskets, BDRY/BWET (where they exist) and SPY |
| Deflated Sharpe | Computed on the holdout returns with the number of trials in `data/results/trials.csv` tagged `research` at registration time |

No parameter, sleeve, universe rule or cost assumption may be changed after this commit
and the holdout re-run. Any later change is reported as a new, separately labelled variant.
