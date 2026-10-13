"""User-confirmed general estimates; investments may override actual costs.

These are planning defaults, not a complete simulation of Currency War income.
Guide-specific labels take precedence over the fallback search-level mapping.
"""
from types import MappingProxyType

RESERVE_GOLD=50
INTEREST_GOLD_STEP=10
INTEREST_CAP=5
REFRESH_COST=2
TARGET_LEVEL_BY_COST=MappingProxyType({1:5,2:6,3:7,4:9,5:9})


def estimated_interest(gold):
    return min(INTEREST_CAP,max(0,gold)//INTEREST_GOLD_STEP)
