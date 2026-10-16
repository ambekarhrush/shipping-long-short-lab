# Pre-registration: booking surprise in results releases (live test)

Committed on 16 October 2026, before any Q3 2026 results release outside the backtest sample
was scored. The backtest (2019 to Q2 2026, 66 releases) found a rank correlation of 0.26
(t 2.2) but was not committed in advance; this test is.

**Signal.** Booking surprise = next-quarter booked rate stated in the results release / the
realised TCE of the quarter reported - 1, extracted by `src/shiplab/filings.py` as of this
commit, without changes to the patterns.

**Outcome.** The stock's total return minus its segment's equal-weighted basket over the 20
trading days starting the first full trading day after the filing.

**Sample.** Every results release filed by the live universe from 17 October 2026 to
31 December 2027 where both fields are extracted.

**Hypothesis.** Rank correlation between signal and outcome is positive.

**Support.** Rank correlation above zero with t above 1.65 (one-sided), and releases with a
surprise above +5% outperforming releases below -5%. Logged in `data/results/trials.csv`;
the sign is not reversed after the fact. Reported whatever the result.
