# FleetWatch live data

Written by the hourly workflow (`.github/workflows/fleetwatch.yml`); do not edit by hand.

* `raw/YYYY/MM/DD/HHMM_static.jsonl.gz`, `..._position.jsonl.gz`: AIS messages for register ships, with receipt time
* `identity.csv`: register ship -> MMSI/IMO match table, with match status
* `daily_states.csv.gz`: ship x day state (underway / anchored / moored, laden / ballast, region)
* `company_signals.csv`: owner x day coverage, idle share, laden share, moving share

The git history of this folder is the timestamped record that each estimate existed before the
company reported.
