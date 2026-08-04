"""Ingest fresh, remote, US-eligible target-title jobs from the bluedoor aggregator.

Bluedoor indexes ~1.6M postings across every ATS. We pull only what matters: a set of
target-title keyword searches, filtered to workplace_type=remote, active, posted in the
last N days. Company name is extracted from source_url (bluedoor stores the ATS as
`provider`, not a clean company). Upserts to Supabase `jobs` as relevant so the morning
agent picks them up.

Run: /Users/zach/.venv/bin/python -m agent.bluedoor_ingest [--days 60] [--per 300]
"""
import os
import re
import sys
import time
import hashlib
import urllib.request
import urllib.error
import json as _json
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from agent import store

load_dotenv()

BASE = "https://api.bluedoor.sh/job-postings/v1/jobs/search"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Title keyword searches (the `q` field is tokenized over title/normalized_title/department).
# These map to the YES + MAYBE buckets in title_rubric.md; the agent's fit gate refines further.
TARGET_QUERIES = [
    "customer success", "customer experience", "customer support", "customer operations",
    "member experience", "client experience", "client success", "customer care",
    "head of support", "support operations", "business operations", "revenue operations",
    "strategy and operations", "customer service",
]

# source_url patterns -> company slug
_HOST_PATTERNS = [
    (r"boards\.greenhouse\.io/([^/]+)", 1),
    (r"job-boards\.greenhouse\.io/([^/]+)", 1),
    (r"jobs\.lever\.co/([^/]+)", 1),
    (r"jobs\.ashbyhq\.com/([^/]+)", 1),
    (r"([^./]+)\.bamboohr\.com", 1),
    (r"([^./]+)\.applytojob\.com", 1),
    (r"([^./]+)\.breezy\.hr", 1),
    (r"([^./]+)\.rippling\.com", 1),
    (r"([^./]+)\.workable\.com", 1),
    (r"jobs\.jobvite\.com/([^/]+)", 1),
    (r"([^./]+)\.myworkdayjobs\.com", 1),
    (r"careers-([^.]+)\.icims\.com", 1),
    (r"([^./]+)\.pinpointhq\.com", 1),
    (r"([^./]+)\.rippling-ats\.com", 1),
    (r"jobs\.smartrecruiters\.com/([^/]+)", 1),
]


def company_from_url(url: str) -> str:
    if not url:
        return ""
    for pat, grp in _HOST_PATTERNS:
        m = re.search(pat, url)
        if m:
            slug = m.group(grp)
            if slug in ("careers", "jobs", "www", "app"):
                continue
            return slug.replace("-", " ").replace("_", " ").title()
    return ""


def _job_hash(url: str) -> str:
    return hashlib.sha256((url or "").encode()).hexdigest()


def _to_int(v):
    try:
        return int(round(float(v))) if v is not None else None
    except (TypeError, ValueError):
        return None


def _post(payload: dict) -> dict:
    key = os.environ["BLUEDOOR_API_KEY"]
    req = urllib.request.Request(
        BASE, data=_json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return _json.load(r)


def fetch(days: int = 60, per_query: int = 300) -> list[dict]:
    """Return de-duplicated bluedoor records for all target queries."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    seen, out = set(), []
    for q in TARGET_QUERIES:
        cursor, pulled = None, 0
        while pulled < per_query:
            payload = {"q": q, "workplace_type": "remote", "posted_after": since,
                       "active": True, "limit": min(100, per_query - pulled),
                       "include_total": False}
            if cursor:
                payload["cursor"] = cursor
            try:
                data = _post(payload)
            except urllib.error.HTTPError as e:
                print(f"  [{q}] HTTP {e.code}: {e.read()[:120]}")
                break
            except Exception as e:
                print(f"  [{q}] error: {e}")
                break
            rows = data.get("data") or []
            for j in rows:
                jid = j.get("job_id") or j.get("source_url") or j.get("apply_url")
                if jid and jid not in seen:
                    seen.add(jid)
                    out.append(j)
            pulled += len(rows)
            cursor = (data.get("meta") or {}).get("next_cursor")
            if not cursor or not rows:
                break
            time.sleep(0.05)
        print(f"  [{q}] pulled ~{pulled}")
    return out


_NON_US = re.compile(r"\b(canada|emea|apac|latam|uk|united kingdom|england|london|europe|"
                     r"germany|berlin|france|paris|ireland|dublin|india|bangalore|australia|"
                     r"singapore|philippines|mexico|brazil|spain|netherlands|poland)\b", re.I)
_US = re.compile(r"\b(us|u\.s\.|usa|united states|remote - us|anywhere,? usa|"
                 r"new york|san francisco|california|texas|boston|seattle|chicago|denver|austin|"
                 r"georgia|florida|virginia|colorado)\b", re.I)


def _us_eligible(loc: str) -> bool:
    loc = loc or ""
    if _US.search(loc):
        return True
    if _NON_US.search(loc):
        return False
    return True  # empty / bare "Remote" -> ambiguous, let the agent's gate decide


def to_row(j: dict) -> dict | None:
    url = j.get("apply_url") or j.get("source_url") or ""
    if not url:
        return None
    title = (j.get("title") or "").strip()
    if not title:
        return None
    if not _us_eligible(j.get("location_text") or ""):
        return None
    company = company_from_url(j.get("source_url") or "") or company_from_url(url) \
        or (j.get("provider") or "").replace("_", " ").title()
    loc = j.get("location_text") or ("Remote" if j.get("workplace_type") == "remote" else "")
    return {
        "url": url, "url_hash": _job_hash(url), "title": title, "company": company,
        "location": loc, "source": "bluedoor", "relevant": True, "is_active": True,
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "date_added": datetime.now(timezone.utc).isoformat(),
        "salary_min": _to_int(j.get("salary_min")), "salary_max": _to_int(j.get("salary_max")),
        "date_posted": (j.get("source_posted_at") or "")[:10] or None,
    }


def ingest(days: int = 60, per_query: int = 300) -> dict:
    from collections import Counter
    from agent import title_filter
    c = store.get_client()
    records = fetch(days, per_query)
    verdicts = Counter()
    rows = []
    for r in (to_row(j) for j in records):
        if not r:
            continue
        v = title_filter.classify(r["title"])
        verdicts[v] += 1
        if v != "no":          # No's never enter the queue (call-center, eng, etc.)
            rows.append(r)
    for i in range(0, len(rows), 200):
        c.table("jobs").upsert(rows[i:i + 200], on_conflict="url_hash",
                               ignore_duplicates=False).execute()
    return {"pulled": len(records), "kept(relevant)": len(rows),
            "dropped_by_title": verdicts["no"], "yes": verdicts["yes"], "maybe": verdicts["maybe"]}


if __name__ == "__main__":
    days = 60
    per = 300
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
    if "--per" in sys.argv:
        per = int(sys.argv[sys.argv.index("--per") + 1])
    print(f"bluedoor ingest: last {days}d, up to {per}/query")
    result = ingest(days, per)
    print(result)
