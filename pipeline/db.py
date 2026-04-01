"""All Supabase read/write operations."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from supabase import create_client, Client
from pipeline.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

_SOURCES_FILE = Path(__file__).parent.parent / "job_sources.json"


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def job_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def get_seen_hashes(client: Client) -> set[str]:
    """Load all seen url_hashes from Supabase."""
    result = client.table("seen_jobs").select("url_hash").execute()
    return {row["url_hash"] for row in (result.data or [])}


def add_seen_hashes(client: Client, hashes: list[str]) -> None:
    """Insert new url_hashes into seen_jobs (ignore conflicts)."""
    if not hashes:
        return
    rows = [{"url_hash": h} for h in hashes]
    for i in range(0, len(rows), 500):
        client.table("seen_jobs").upsert(
            rows[i:i+500], on_conflict="url_hash"
        ).execute()


def get_sources(client: Client) -> list[dict]:
    """Return all sources from job_sources.json (git-managed)."""
    data = json.loads(_SOURCES_FILE.read_text())
    return data.get("sources", [])


def upsert_jobs(client: Client, jobs: list[dict]) -> int:
    """Upsert raw scraped jobs. Returns count of rows sent."""
    if not jobs:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    seen_hashes: dict[str, dict] = {}
    for job in jobs:
        url = job.get("url", "")
        if not url:
            continue
        h = job_hash(url)
        if h in seen_hashes:
            continue
        seen_hashes[h] = {
            "title":     job.get("title", ""),
            "company":   job.get("company", ""),
            "location":  job.get("location", ""),
            "url":       url,
            "url_hash":  h,
            "source":    job.get("source", ""),
            "work_type": _detect_work_type(job.get("location", "")),
            "is_active": True,
            "last_seen": now,
        }
    rows = list(seen_hashes.values())
    total = 0
    for i in range(0, len(rows), 500):
        batch = rows[i:i+500]
        client.table("jobs").upsert(batch, on_conflict="url_hash").execute()
        total += len(batch)
    return total


def get_unfiltered_jobs(client: Client) -> list[dict]:
    """All jobs not yet marked relevant (across all time)."""
    result = (
        client.table("jobs")
        .select("url_hash, title, location")
        .eq("relevant", False)
        .execute()
    )
    return result.data or []


def mark_relevant(client: Client, url_hashes: list[str]) -> None:
    """Set relevant=true on jobs that passed the pre-filter."""
    if not url_hashes:
        return
    for i in range(0, len(url_hashes), 500):
        batch = url_hashes[i:i+500]
        client.table("jobs").update({"relevant": True}).in_("url_hash", batch).execute()


def get_jobs_to_enrich(client: Client, limit: int = 100) -> list[dict]:
    """Relevant jobs that have no description yet."""
    result = (
        client.table("jobs")
        .select("id, url, url_hash, title, company")
        .eq("relevant", True)
        .is_("enriched_at", "null")
        .eq("is_active", True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def save_description(client: Client, url_hash: str, description: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    client.table("jobs").update({
        "description": description,
        "enriched_at": now,
    }).eq("url_hash", url_hash).execute()


SCORE_CUTOFF_DATE = "2026-03-31"

def get_jobs_to_score(client: Client, limit: int = 100) -> list[dict]:
    """Enriched jobs that have no score yet, added on or after SCORE_CUTOFF_DATE."""
    result = (
        client.table("jobs")
        .select("id, url_hash, title, company, location, description")
        .eq("relevant", True)
        .not_.is_("enriched_at", "null")
        .is_("scored_at", "null")
        .eq("is_active", True)
        .gte("date_added", SCORE_CUTOFF_DATE)
        .limit(limit)
        .execute()
    )
    return result.data or []


def save_score(client: Client, url_hash: str, score: float, reasoning: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    client.table("jobs").update({
        "match_score":     score,
        "match_reasoning": reasoning,
        "scored_at":       now,
    }).eq("url_hash", url_hash).execute()


def _detect_work_type(location: str) -> str:
    loc = location.lower() if location else ""
    if "hybrid" in loc:
        return "hybrid"
    if "remote" in loc:
        return "remote"
    if any(city in loc for city in ["new york", "san francisco", "chicago",
                                     "seattle", "boston", "austin", "denver"]):
        return "onsite"
    return "unknown"
