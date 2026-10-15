# 04 · FleetWatch

**Question.** Can ship-level tracking of each listed owner's fleet see what the market prices
late: utilisation, idle time, geography?

**What exists today.** A register of about 1,000 operating ships mapped to 21 listed dry bulk
and tanker owners, extracted from the companies' own SEC filings (with charter terms where
disclosed), and an AIS collector that records them every hour into this repository. Every
estimate is committed before the company reports, so the live record cannot be fitted after
the fact.

![FleetWatch register](../figures/04_fleet_register.png)

**Why this, and not raw AIS.** Large funds buy global AIS. What is not sold as a package is the
mapping from ships to small, thinly covered listed owners, and a model of each owner's quarter.
Project 02 shows aggregate AIS adds nothing; the information is in the attribution.

| Layer | Source | Status |
|---|---|---|
| Fleet register | SEC 20-F / 10-K fleet tables, Diana fleet employment 6-K, company fleet pages | ~1,000 ships, 21 owners |
| AIS identity (MMSI/IMO) | aisstream.io static reports, matched by name, type and hull length | building, hourly |
| Ship state: underway / waiting / alongside, laden / ballast, region | AIS positions and draught, PortWatch ports | building, hourly |
| Company signals: idle share, regional exposure | aggregation by deadweight | forward from October 2026 |
| Historical test, US waters 2015-2025 | NOAA AIS, point-in-time fleets from every annual report since 2014 | pre-registered, in progress |

**The 2026 Hormuz test case.** When the strait closed on 28 February 2026, more than 150
tankers waited outside it. Which owners had ships trapped in the Gulf, and which were positioned
to gain from Cape routing, mattered more to their quarter than any index. That is exactly the
exposure FleetWatch measures.

**First scored season:** Q4 2026 results (February 2027).

| | |
|---|---|
| Notebook | [`notebooks/fleetwatch.ipynb`](notebooks/fleetwatch.ipynb) |
| Register | [`data/reference/fleet_register.csv`](../data/reference/fleet_register.csv) |
| Live data | [`data/fleet/`](../data/fleet) (written by the hourly workflow) |
| Code | [`src/shiplab/fleet/`](../src/shiplab/fleet), [`.github/workflows/fleetwatch.yml`](../.github/workflows/fleetwatch.yml) |
| Pre-registration (history test) | [`docs/PREREGISTRATION_FLEET_HISTORY.md`](../docs/PREREGISTRATION_FLEET_HISTORY.md) |

**Previous:** [← 03 · Market-neutral long/short](../03-market-neutral-long-short)
