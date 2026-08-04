"""Rules-based title classifier: Yes / Maybe / No. The free first pass of the funnel.

Implements title_rubric.md. Deterministic, instant, zero cost. Runs on every ingested
title before any JD fetch or LLM scoring. See title_rubric.md for the spec.
"""
import re

# Hard NO: wrong function or non-professional, regardless of anything else.
_NO = re.compile(
    r"\b(engineer|engineering|developer|swe|devops|sre|architect|"
    r"phlebotomist|technician|clinician|nurse|physician|therapist|driver|cashier|"
    r"call\s*center|field\s*service|field\s*support|"
    r"sales\s+rep|sales\s+representative|account\s+executive|\bae\b|\bsdr\b|\bbdr\b|"
    r"recruit|talent\s+acquisition|counsel|attorney|paralegal|accountant|controller|bookkeep|"
    r"intern\b|apprentice|"
    r"marketing|brand|\bseo\b|paid\s+media|content\s+writer|copywriter|"
    r"graphic|product\s+design|ux\s+design|ui\s+design|"
    r"data\s+scientist|machine\s+learning|forward\s+deployed|"
    r"workplace|facilities|executive\s+assistant|receptionist|"
    r"warehouse|logistics\s+associate|installer)\b", re.I)

# MAYBE: genuinely ambiguous, send to the Review queue.
_MAYBE = re.compile(r"\b(revenue\s+operations|revops|product\s+manager|program\s+manager|"
                    r"growth\s+strategy|gtm)\b", re.I)

# YES core functions (leadership OR IC in Zach's wheelhouse).
_YES = re.compile(r"\b(customer\s+success|customer\s+experience|member\s+experience|"
                  r"client\s+success|client\s+experience|customer\s+operations|"
                  r"business\s+operations|support\s+operations|strategy\s+and\s+operations|"
                  r"strategy\s+&\s+operations|head\s+of\s+support|chief\s+of\s+staff|"
                  r"\bcx\b|customer\s+support|customer\s+care|customer\s+service)\b", re.I)

# Level signals: a customer-facing role needs to be at least this senior to be YES.
_SENIOR = re.compile(r"\b(manager|lead|director|head|senior|\bsr\.?\b|principal|"
                     r"vp|vice\s+president|chief|founding|strategic|enterprise|staff)\b", re.I)
# Entry-level markers that pull a customer/support role down to NO unless senior.
_ENTRY = re.compile(r"\b(representative|\brep\b|associate|coordinator|agent|specialist|"
                    r"assistant|advocate|analyst\s+i\b|tier\s*[12])\b", re.I)


def classify(title: str) -> str:
    t = title or ""
    if _NO.search(t):
        return "no"
    if _MAYBE.search(t) and not _YES.search(t):
        return "maybe"
    if _YES.search(t):
        # a wheelhouse function — but a low-level, non-senior one is still a No
        if _ENTRY.search(t) and not _SENIOR.search(t):
            return "no"
        return "yes"
    # touches ops/customer language but not a core function: senior -> Maybe, else No
    if re.search(r"\b(operations|customer|success|experience|support)\b", t, re.I):
        return "maybe" if _SENIOR.search(t) else "no"
    return "no"
