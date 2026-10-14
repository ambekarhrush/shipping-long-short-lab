"""Rebuild identity table, daily ship states and company signals from all raw snapshots."""

from __future__ import annotations

import pandas as pd

from ..config import DATA, REFERENCE
from . import identity, status


def main() -> None:
    static = identity.load_static()
    ids = identity.build(static)
    pos = status.load_positions()
    ports = pd.read_csv(REFERENCE / "ports.csv")
    states = status.daily_states(pos, static, ports)
    out = DATA / "fleet"
    if len(states):
        states.to_csv(out / "daily_states.csv.gz", index=False)
        sig = status.company_signals(states, ids[ids["status"] == "matched"])
        sig.to_csv(out / "company_signals.csv", index=False)
    summary = ids["status"].value_counts().to_dict()
    print({"identity": summary, "ship_days": len(states)})


if __name__ == "__main__":
    main()
