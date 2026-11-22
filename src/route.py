"""
ROUTE: decide who owns each company.
  1. Already in the CRM with an owner -> keep that owner (never steal accounts).
  2. Tier A or B in DACH/Benelux -> the DACH team, in turn (round-robin).
  3. Tier A or B elsewhere -> the other team, in turn.
  4. Tier C -> marketing nurture, not a rep.
"""

from itertools import cycle

import config as c

_dach = cycle(c.DACH_TEAM)
_other = cycle(c.OTHER_TEAM)


def assign_owner(row, existing_owner):
    if existing_owner:
        return existing_owner, "existing owner kept"
    if row["tier"] == "C":
        return c.NURTURE_OWNER, "tier C -> nurture"
    if row.get("country") in c.TARGET_COUNTRIES:
        return next(_dach), "DACH/Benelux round-robin"
    return next(_other), "other-region round-robin"
