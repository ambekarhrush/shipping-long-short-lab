# Data sources

All sources are free. Raw vendor files are not redistributed; scripts rebuild them.

| Data | Source | Access | Used for |
|---|---|---|---|
| Prices, dividends, splits (survivors) | Yahoo Finance via `yfinance` | no key | total returns, liquidity |
| Prices of delisted US names | Tiingo end-of-day API | free key in `.env` (`TIINGO_API_KEY`) | survivorship |
| USD/NOK | Federal Reserve H.10 (FRED `DEXNOUS`) | no key | Oslo-listed returns |
| Fundamentals | SEC EDGAR XBRL company facts | no key (User-Agent with contact) | value, balance-sheet strength |
| Fleet lists | SEC 20-F / 10-K fleet tables, Diana fleet employment 6-K, company fleet pages | no key | FleetWatch register |
| Baltic indices (BDI, BCI, BPI, BSI, BHSI, BDTI, BCTI, BLPG, BLNG) | Barchart price-history pages | free account; save as `data/manual/baltic_indices_barchart_*.csv` (`symbol,date,close`) | freight model |
| Freight ETFs | BDRY, BWET via Yahoo | no key | benchmarks |
| Port calls, trade volumes, chokepoint transits | IMF PortWatch (ArcGIS) | no key | segment activity (2019+) |
| Ports with coordinates | IMF PortWatch ports database | no key | FleetWatch port proximity |
| AIS positions and static reports | aisstream.io websocket | free key (`AISSTREAM_API_KEY`) | FleetWatch |

## Known vendor problems found and handled

* Yahoo `NOK=X` prints 7.74 on 2020-03-20 (official 11.68): FX taken from FRED instead.
* Yahoo adjusted close missed 2020 Bulkers' NOK 131.44 liquidating distribution (2026-04-29):
  total returns rebuilt from prices and cash distributions.
* Tickers recycled by unrelated securities (BALT, EGLE, GOGL, GRIN): free vendors return only
  the new security, so the old companies are documented gaps.
* TORM's Nasdaq line traded near-zero volume until April 2020: enters the universe then.
* Bad one-day prints that fully reverse the next day are collapsed and logged
  (`shiplab.panel.repair_bad_prints`).
