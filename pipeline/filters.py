"""Relevance pre-filter: pure function, no I/O.

Only jobs passing this filter get enriched (JD fetched) and scored (Haiku API).
This keeps costs down and prevents marketing/engineering/HR roles from polluting results.
"""
from pipeline.config import (
    INCLUDE_TITLE_KEYWORDS,
    EXCLUDE_TITLE_KEYWORDS,
    US_LOCATION_KEYWORDS,
    NON_US_LOCATION_KEYWORDS,
)


def is_relevant(title: str, location: str) -> bool:
    """
    Returns True if a job should be enriched and scored.

    Criteria:
      - Title contains at least one INCLUDE keyword
      - Title contains no EXCLUDE keywords
      - Location is US, unspecified, or ambiguously remote (not a non-US country)
    """
    t   = title.lower() if title else ""
    loc = location.lower() if location else ""

    # Must match at least one CX/ops keyword
    if not any(kw in t for kw in INCLUDE_TITLE_KEYWORDS):
        return False

    # Exclude non-CX roles
    if any(kw in t for kw in EXCLUDE_TITLE_KEYWORDS):
        return False

    # Location check: reject if clearly non-US with no US counterpart
    is_non_us = any(kw in loc for kw in NON_US_LOCATION_KEYWORDS)
    is_us     = any(kw in loc for kw in US_LOCATION_KEYWORDS)

    if is_non_us and not is_us:
        return False

    return True
