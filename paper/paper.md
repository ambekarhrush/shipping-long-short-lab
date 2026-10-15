---
title: "Priced by Friday"
subtitle: "What fifteen years of listed shipping equities say about where a stock-selection edge can come from"
author: "Hrushikesh Ambekar"
date: "October 2026"
---

*Independent research project. Not affiliated with, endorsed by or produced for any current,
previous or future employer of the author. Public data only. Not investment advice.*

## Summary

Listed shipping looks like the ideal hunting ground for a stock picker. A few dozen companies
share the same handful of drivers (freight rates, ship values, fleet supply, balance sheets), yet
their share prices diverge enormously. Within one segment in a typical year, the gap between
the upper- and lower-quartile stock's 12-month return is about 30 percentage points, and it
exceeded 100 points in every segment's boom years. Coverage is thin. Much of
the information that matters is, in principle, observable.

We tested whether that divergence can be harvested market-neutrally, using only public data, on
54 New York- and Oslo-listed shipping companies from 2011 to October 2026, keeping the companies
that merged, went bankrupt or changed business. The work was built to be hard to fool: every
variant tried was logged automatically, parameters were chosen year by year on past data only,
and the final configuration was committed to git before a sealed 2023-2026 holdout was run once.

Four findings.

1. **Public freight data is priced within the week.** Weekly changes in the Baltic indices and
   in segment equity baskets are correlated contemporaneously (about 0.35 in dry bulk and
   tankers) and have essentially no predictive relationship a month out in dry bulk. Freight
   momentum, on its own or used to time other signals, added nothing.
2. **Inside a segment, cheapness and dislocation work, modestly.** Ranking companies within their
   segment on book-to-market, and fading moves that are out of line with a stock's own freight
   sensitivity, produced a Sharpe ratio of 0.70 in walk-forward testing (2014-2020), 0.61 in
   validation (2021-2022) and **0.42 in the sealed holdout**, with a market beta of essentially
   zero. A pre-registered hypothesis, that balance-sheet strength pays only when freight is
   falling, was rejected.
3. **The return is small and capacity-constrained.** At a USD 10m reference fund it earned about
   2-4% a year at 5% volatility. Because these stocks trade a few million dollars a day, the
   Sharpe ratio falls from about 0.8 at USD 2m to 0.45 at USD 50m, and the dollar return
   plateaus below USD 1m a year.
4. **After correcting for the search, the public-data edge is not statistically distinguishable
   from luck.** With 27 logged research variants, the deflated-Sharpe probability of the holdout
   result is 0.31.

The perspective that follows is the point of the project. If the market absorbs public freight
data within days, and public fundamentals yield only a small, uncertain edge, then a durable
edge in shipping equities must come from information about individual companies that reaches
the market late: where each owner's ships are, whether they are loaded, idle or off-hire, how
much of next quarter is already fixed. That information is observable from ship-tracking data
(AIS), but only if one knows which ships belong to which listed company. We built that mapping
from the companies' own filings (about 1,000 ships of 21 owners) and started recording it,
hourly, in public, before each company reports. That forward record, not another backtest, is
what can show whether the edge is real.

## 1. Why shipping, and why it is hard

Shipping equities are levered, finite-life claims on volatile freight markets. Companies in the
same segment carry the same freight exposure but differ in four ways that matter: fleet age
and specification, leverage, how much of their fleet is fixed on time charter, and what
management does with cash (buybacks, dividends, newbuildings, dilution). Those differences
should produce persistent, tradable gaps within each segment.

Three things make the opportunity harder than it looks.

* **The universe is small.** At any time there are 25-40 relevant listed names across dry bulk,
  crude and product tankers, containers and gas carriers. A segment-neutral book needs at least
  four tradable names per segment; container owners met that bar only from 2021 (Figure 4).
* **Liquidity is thin.** The median stock traded a few million dollars a day for most of the
  period. Many small caps were serial diluters with repeated reverse splits.
* **History is treacherous.** Companies merge, go bankrupt, change business and hand their
  tickers to unrelated securities. A careless backtest silently splices in the wrong company.

## 2. Getting the history right

Before any signal was tested, the data audit (notebook 01) established which companies belonged
to the opportunity set on each date and corrected vendor errors that would otherwise have
manufactured results.

* **A point-in-time register of 73 companies.** Each is in the universe only while it was a
  listed pure-play in its segment. Twenty-nine names left during the period (mergers,
  take-privates, bankruptcies, change of business). Nineteen are excluded or are documented
  gaps, including four merged companies whose tickers were later recycled by exchange-traded
  funds, so free vendors now return the wrong security.
* **Total returns were rebuilt**, not downloaded. One vendor's adjusted prices missed 2020
  Bulkers' NOK 131-per-share liquidating distribution, which would have appeared as a 96% loss.
* **Official FX.** A single bad USD/NOK print in a popular free source would have created a +45%
  day followed by a -35% day in every Oslo-listed stock on 20 March 2020.
* **Takeover freeze.** From the day a bid became public, the target trades on deal terms rather
  than fundamentals. Signals are frozen from that date, which currently applies to ZIM (cash
  offer from Hapag-Lloyd) and Genco (contested bid from Diana).

Survivorship bias in shipping turned out to cut both ways. Most exits were takeovers at a
premium, which survivor-only backtests miss; the bankruptcies, which survivor-only backtests
also miss, are precisely the names for which free price history no longer exists. The net
measured effect on an equal-weighted index is small, but it is small partly because the worst
outcomes cannot be measured. We state this as a limitation rather than a correction.

## 3. Fifteen years in four segments

[Figure 1: equity baskets against their Baltic indices]

The period contains every kind of shipping market: the 2015-16 dry bulk collapse (the Baltic
Dry Index at its lowest ever, followed by restructurings); a long tanker drought; the 2020
pandemic shock and floating-storage spike; the 2021-22 container boom; the 2022 sanctions on
Russian oil, which rerouted tanker trade; the 2023-24 Red Sea attacks, which sent ships around
the Cape; and, in 2026, the closure of the Strait of Hormuz after strikes on Iran, when VLCC
earnings exceeded USD 400,000 a day.

Two features of this history motivate the strategy. Equity baskets and their freight indices
share cycles but not levels, because equity holders also bear dilution, leverage and capital
allocation. And within each segment, outcomes diverged widely in every year (Figure 2).

[Figure 2: within-segment dispersion of 12-month returns]

## 4. Finding one: freight is priced within the week

[Figure 3: lead-lag between freight indices and equity baskets]

We compared weekly changes in each segment's equal-weighted equity basket with weekly changes
in its Baltic index, at leads and lags of up to eight weeks, over 2011-2022. The relationship
peaks at lag zero: about 0.37 in dry bulk and 0.33 in tankers. Over a four-week horizon,
equity moves do not predict freight in either segment, and freight does not predict dry bulk
equities (correlation -0.05). Tankers show a modest delayed response (0.18), the only sign of
underreaction to public freight data.

The implication is practical. Signals built on public freight indices, such as freight momentum
or timing exposure to the freight cycle, should not be expected to add much once trading costs
are paid. That is what we found: freight-beta momentum had a within-segment information
coefficient indistinguishable from zero in every segment, and it neither helped nor hurt the
factor sleeve.

The same is true of *aggregate* ship-tracking data. Using the IMF's PortWatch transit counts
(2019-2026), we tested whether shifts in tanker or dry bulk tonnage through the major chokepoints
(the share routed via the Cape rather than Suez, tonnage through Hormuz and Malacca) predict the
next month's freight index. None did: every correlation with the following four weeks of freight
was below 0.09 in absolute value. Aggregate AIS data, like the Baltic indices, describes the
market everyone already sees. Its value, if any, lies in attributing ships to specific companies.

## 5. Finding two: what works inside a segment

The strategy has three sleeves, each neutral to segment exposure.

1. **Pairs.** Mean reversion between similar companies, re-selected each quarter. It rarely
   found stable pairs in such a small universe, earned nothing in walk-forward testing and was
   excluded before the holdout.
2. **Factor ranks.** Long the best-ranked, short the worst-ranked third of each segment on a
   composite of book-to-market, balance-sheet strength and freight-beta momentum.
3. **Equity versus freight.** Each stock's return is regressed on its segment's freight index
   and on the market over the previous year; when the stock's recent return departs from what
   that relationship implies, the sleeve trades it back.

Two components earned their place: **cheapness within the segment** and **fading
freight-unexplained moves**. Balance-sheet strength, on its own, did nothing across the whole
universe, but this masks a split: it was rewarded in dry bulk (information coefficient 0.15,
t = 2.1) and penalised among container owners (-0.24, t = -2.1), where leverage was rewarded in
the 2021-22 boom.

Before testing, we registered a specific hypothesis: that a strong balance sheet works like a
low option strike, paying off when freight falls and costing when it rises, so that holding
strength in falling markets and leverage in rising ones would earn a return. It did not
(Sharpe -0.24 and -0.56 on two horizons). We report it as rejected and did not reverse the sign.

## 6. Finding three: neutral, positive, small

[Figure 4: strategy against the S&P 500 and the shipping basket, with drawdowns]

| Period | Sharpe | Return p.a. | Volatility | Max drawdown | Beta |
|---|---|---|---|---|---|
| Walk-forward 2014-2020 | 0.70 | 3.6% | 5.2% | -7.5% | 0.03 |
| Validation 2021-2022 | 0.61 | 3.3% | 5.5% | -5.1% | 0.01 |
| Sealed holdout 2023 - Oct 2026 | 0.42 | 2.1% | 5.3% | -7.2% | -0.01 |

The return is genuinely market-neutral: its daily correlation is 0.06 with the S&P 500 and
-0.02 with the shipping basket. Both books contributed: the longs about 1.6% a year and the
shorts about 2.1%, before the hedge and costs. By segment, the largest contributions came from
tankers and containers on the long side and gas carriers on both sides.

[Figure 5]

In stress windows the strategy behaved as intended in four of five episodes: +4.4%
through the 2015-16 dry bulk trough while the shipping basket fell 36%, roughly flat through
the COVID shock and the 2022 sanctions, +5.3% through the Red Sea disruption. It lost 5.0% in
the 2026 Hormuz crisis, when tanker equities re-rated violently and within-segment relationships
broke down.

[Figure 6]

**Capacity.** Positions were limited to 10% of a stock's typical daily traded value. At USD 2m
the Sharpe ratio is about 0.8; at USD 25m about 0.6; at USD 50m about 0.45. The dollar return
plateaus below USD 1m a year. This is a niche strategy, suitable as a sleeve within a broader
book or for a small specialist fund, not as a standalone product.

**Costs.** At the reference size, trading and borrow costs absorbed about 0.7% a year. Doubling
every spread and borrow assumption reduces the Sharpe ratio from 0.68 to 0.56.

## 7. Finding four: honest statistics

[Figure 7: every research variant tried]

Every variant that was ever run was written automatically to a trials ledger: 27 research
variants in all, plus capacity and cost-sensitivity runs that do not change the design. The
deflated Sharpe ratio asks how likely the observed result is to beat the best of 27 unskilled
strategies with the same spread of outcomes. For the holdout, the answer is 0.31; conventional
confidence would require 0.95.

This is the result we would expect if the public-data edge is real but small, and the sample
is short. It is not the result one would get from a strategy worth launching on its own.

## 8. The implication: information that arrives late

If public freight data is priced within days, and public fundamentals yield only a small edge,
where could a durable edge come from? The candidates share a feature: they describe an
individual company's operations before the company reports them.

* **Fleet utilisation.** How many of a company's ships are trading, idle at anchor, or in
  drydock this quarter.
* **Spot exposure.** How many of next quarter's days are still open to the spot market, which
  companies disclose only at results.
* **Geography.** Where each company's ships are relative to where rates are moving. In March
  2026, more than 150 tankers were anchored outside the Strait of Hormuz; which owners had
  ships inside the Gulf, and which had ships positioned to benefit from Cape routing, mattered
  more to their quarter than any index.

All of this is observable from AIS, the transponder data every large ship broadcasts. Large
funds buy it in bulk. What they do not get in a package is the mapping from ships to small,
thinly covered listed owners, and a model of each owner's quarter.

**FleetWatch** is that mapping and model.

1. **Fleet register.** About 1,000 operating ships of 21 listed dry bulk and tanker owners,
   extracted from their own annual reports and fleet employment tables, with deadweight, age
   and charter terms where disclosed. Each row records its source filing and date.
2. **Identity.** Each ship is linked to its AIS identity using broadcast name, type and hull
   dimensions; ambiguous matches are listed, not guessed.
3. **Ship states.** Daily state for each ship: underway, waiting at anchor, or alongside;
   laden or in ballast (from reported draught relative to the deepest draught seen); and
   region.
4. **Company signals.** Idle share, laden share and regional exposure by owner, aggregated by
   deadweight.

The collector runs every hour and commits its output to the public repository. The commit
history therefore proves that each estimate existed before the corresponding earnings release.
The first test is the Q4 2026 reporting season in February 2027.

## 9. Limitations

* The universe is small and often illiquid; results at sizes above USD 25m are not meaningful.
* Vessel values are not available point-in-time from free sources; book value stands in for net
  asset value, which understates the true dispersion in asset backing.
* Borrow costs are modelled by liquidity tier, not observed. Some small caps would have been
  unavailable to borrow.
* Free price history is missing for several bankruptcies and four merged companies whose
  tickers were recycled; their absence biases measured returns upwards.
* Oslo-only companies lack machine-readable fundamentals and are excluded from fundamental ranks.
* FleetWatch uses terrestrial AIS, which loses ships in mid-ocean. Port events are reliable;
  speed between ports is not. Laden status needs one observed loaded voyage per ship before it
  is reliable.

## Appendix: method

* **Universe and screens.** Point-in-time register; tradable when the 60-day median daily
  value is at least USD 1m, price at least USD 2 and no takeover is pending.
* **Returns.** Rebuilt from as-traded prices, cash distributions and split ratios; NOK
  converted at the Federal Reserve H.10 rate; zero-volume days treated as no trade.
* **Fundamentals.** SEC XBRL company facts, entered the day after filing.
* **Freight.** Baltic Exchange indices (dry, capesize, panamax, supramax, handysize, dirty and
  clean tanker, LPG), daily from 2006.
* **Portfolio.** Sleeves scaled to 6% ex-ante volatility; per-name cap 7.5% of NAV; gross cap
  250%; positions at most 10% of daily traded value; residual beta hedged with SPY; drawdown
  brake at -15%; one-day trading lag; half-spread 5-60 bp and square-root impact; borrow 0.5-15%
  a year by liquidity tier.
* **Validation.** Parameters chosen each year on prior data (2014-2022); holdout 2023 to
  October 2026 sealed in code and pre-registered in git; deflated Sharpe ratio (Bailey and
  Lopez de Prado, 2014) over all logged research variants.
* **Reproduction.** `scripts/run_research.py --holdout` rebuilds every number from raw data.
