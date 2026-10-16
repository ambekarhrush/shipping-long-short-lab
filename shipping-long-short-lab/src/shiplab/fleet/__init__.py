"""FleetWatch: ship-level tracking of the listed fleets.

Pipeline
--------
1. ``register``  company -> vessel register built from SEC filings and company fleet pages
                 (``data/reference/fleet_register.csv``; every row carries its source and
                 as-of date).
2. ``ais``       live AIS collector (aisstream.io). Raw messages are filtered to the
                 register's ships and stored append-only with receipt timestamps.
3. ``identity``  links register vessels to MMSI/IMO using AIS static reports (name, type,
                 dimensions), with an auditable match table.
4. ``status``    turns position and draught reports into daily ship states (laden/ballast,
                 underway/at anchor/in port, region) and voyage events.
5. ``nowcast``   aggregates states to company level: open spot days, idle/off-hire days,
                 laden share, regional exposure -> earnings nowcast vs guidance.

Everything from step 2 onward is forward-only: it starts on the date collection began and
every estimate is committed to git before the company reports, so the live record cannot
be fitted after the fact.
"""
