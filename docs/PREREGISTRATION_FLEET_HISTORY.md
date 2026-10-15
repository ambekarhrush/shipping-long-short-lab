# Pre-registration: historical test of ship-level signals (US-waters AIS)

Committed before any ship-level signal was compared with stock returns.

**Data.** NOAA MarineCadastre AIS for US waters, one sampled day per week (Wednesdays),
January 2015 to December 2025, ships of 140 m or more, hourly resolution. Ships are attributed to
owners using fleet tables from each company's annual report, effective from the filing date
(point in time). Dry bulk and tanker owners only.

**Ship state on a sampled day** (last observation of the day):
* *idle*: speed below 1 knot and not within 5 nautical miles of a PortWatch port;
* *laden*: reported draught at least 75% of the deepest draught observed for that ship so far.

**Hypotheses** (company-month signals over the trailing eight sampled weeks, ranked within
segment among companies with at least three observed ship-days):

* **H1, idle share (sign: negative).** Owners with a larger share of observed ship-days idle
  underperform their segment over the next month.
* **H2, laden share (sign: positive).** Owners with a larger share of observed ship-days laden
  outperform their segment over the next month.

**Test.** Monthly, long the top third and short the bottom third of each segment on each signal,
equal-weighted, next-month total return, 2016-01 to 2025-12. Report the mean monthly rank
information coefficient with its t-statistic, and the long/short Sharpe ratio. Both are logged
in `data/results/trials.csv`; the deflated Sharpe ratio counts them with all earlier trials.

**What would count as support.** IC t-statistic above 2 with the registered sign, for either
hypothesis. Signs are not reversed after the fact. US waters show only part of each fleet's
activity, so a null result does not reject the global FleetWatch design.
