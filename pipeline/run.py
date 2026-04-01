#!/usr/bin/env python3
"""
Job Monitor Pipeline — four phases per run:

  Phase 1 — Scrape:  Hit all enabled sources, upsert raw jobs to Supabase,
                     record new url_hashes in seen_jobs.
  Phase 2 — Filter:  Mark relevant=true on jobs passing the title/location filter.
  Phase 3 — Enrich:  Fetch full JD text for relevant unenriched jobs.
  Phase 4 — Score:   Call Claude Haiku for enriched unscored jobs.

Run:   python -m pipeline.run
Cron:  0 14,20 * * *  (10am + 4pm EST)
"""
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from playwright.sync_api import sync_playwright

from pipeline import config


def _ping(suffix: str = "") -> None:
    """Ping healthchecks.io. Silently no-ops if HEALTHCHECK_URL is not set."""
    if not config.HEALTHCHECK_URL:
        return
    try:
        url = config.HEALTHCHECK_URL.rstrip("/") + (f"/{suffix}" if suffix else "")
        urllib.request.urlopen(url, timeout=5)
    except Exception:
        pass  # never let monitoring break the pipeline
from pipeline.db import (
    get_client, get_seen_hashes, add_seen_hashes,
    get_sources, upsert_jobs, mark_relevant,
    get_unfiltered_jobs, get_jobs_to_enrich, save_description,
    get_jobs_to_score, save_score, job_hash,
)
from pipeline.filters import is_relevant
from pipeline.enricher import fetch_description
from pipeline.scorer import score_job
from pipeline.scrapers import (
    ashby, greenhouse, lever, vc_boards,
    startups_gallery, career_page, workatastartup,
)

SCRAPER_MAP = {
    "ashby":          ashby.scrape,
    "greenhouse":     greenhouse.scrape,
    "lever":          lever.scrape,
    "vc_job_board":   vc_boards.scrape,
    "playwright":     startups_gallery.scrape,
    "career_page":    career_page.scrape,
    "workatastartup": workatastartup.scrape,
}


# ── Phase 1 ───────────────────────────────────────────────────────────────────

def phase1_scrape(client) -> list[dict]:
    """Scrape all enabled sources. Returns all raw jobs found this run."""
    sources     = get_sources(client)
    seen_hashes = get_seen_hashes(client)
    print(f"\n[Phase 1] Scraping {len(sources)} sources...")

    all_jobs: list[dict] = []

    def scrape_source(source: dict) -> list[dict]:
        scraper = SCRAPER_MAP.get(source.get("type", ""))
        if not scraper:
            print(f"  No scraper for type '{source.get('type')}' ({source.get('name')})")
            return []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    return scraper(browser, source)
                finally:
                    browser.close()
        except Exception as e:
            print(f"  Error scraping {source.get('name')}: {e}")
            return []

    with ThreadPoolExecutor(max_workers=config.MAX_SCRAPE_WORKERS) as executor:
        futures = {executor.submit(scrape_source, s): s for s in sources}
        for future in as_completed(futures):
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"  Scrape future error: {e}")

    print(f"  Total raw jobs scraped: {len(all_jobs)}")

    inserted = upsert_jobs(client, all_jobs)
    print(f"  Upserted {inserted} jobs to Supabase")

    new_hashes = [
        job_hash(j["url"])
        for j in all_jobs
        if j.get("url") and job_hash(j["url"]) not in seen_hashes
    ]
    add_seen_hashes(client, new_hashes)
    print(f"  Added {len(new_hashes)} new hashes to seen_jobs")

    return all_jobs


# ── Phase 2 ───────────────────────────────────────────────────────────────────

def phase2_filter(client) -> None:
    """Mark relevant=true on unfiltered jobs (DB-driven, all time)."""
    jobs = get_unfiltered_jobs(client)
    print(f"\n[Phase 2] Filtering {len(jobs)} unfiltered jobs...")
    relevant_hashes = [
        j["url_hash"]
        for j in jobs
        if is_relevant(j.get("title", ""), j.get("location", ""))
    ]
    mark_relevant(client, relevant_hashes)
    print(f"  Marked {len(relevant_hashes)} jobs as relevant "
          f"({len(jobs) - len(relevant_hashes)} filtered out)")


# ── Phase 3 ───────────────────────────────────────────────────────────────────

def phase3_enrich(client) -> None:
    """Fetch JD text for relevant unenriched jobs."""
    jobs = get_jobs_to_enrich(client, limit=config.ENRICH_BATCH_SIZE)
    print(f"\n[Phase 3] Enriching {len(jobs)} jobs...")
    if not jobs:
        print("  Nothing to enrich.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for i, job in enumerate(jobs, 1):
                desc = fetch_description(browser, job["url"])
                save_description(client, job["url_hash"], desc)
                if i % 10 == 0:
                    print(f"  Enriched {i}/{len(jobs)}...")
        finally:
            browser.close()

    print(f"  Enrichment complete: {len(jobs)} jobs processed")


# ── Phase 4 ───────────────────────────────────────────────────────────────────

def phase4_score(client) -> None:
    """Score enriched jobs with Claude Haiku."""
    jobs = get_jobs_to_score(client, limit=config.SCORE_BATCH_SIZE)
    print(f"\n[Phase 4] Scoring {len(jobs)} jobs...")
    if not jobs:
        print("  Nothing to score.")
        return

    for i, job in enumerate(jobs, 1):
        score, reasoning = score_job(
            job["title"], job["company"], job.get("description", "")
        )
        save_score(client, job["url_hash"], score, reasoning)
        if i % 10 == 0:
            print(f"  Scored {i}/{len(jobs)}...")

    print(f"  Scoring complete: {len(jobs)} jobs processed")

    # Print top matches from this batch
    result = (
        client.table("jobs")
        .select("title, company, location, url, match_score, match_reasoning")
        .not_.is_("scored_at", "null")
        .gte("match_score", config.MIN_MATCH_SCORE)
        .order("scored_at", desc=True)
        .limit(10)
        .execute()
    )
    top = result.data or []
    if top:
        print(f"\n  Top matches (score >= {config.MIN_MATCH_SCORE}):")
        for job in sorted(top, key=lambda x: x.get("match_score", 0), reverse=True):
            print(f"  [{job['match_score']:.1f}] {job['title']} @ {job['company']}")
            print(f"        {job.get('match_reasoning', '')}")
            print(f"        {job['url']}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"Job Monitor Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    _ping("start")
    try:
        client   = get_client()
        phase1_scrape(client)
        phase2_filter(client)
        phase3_enrich(client)
        phase4_score(client)
    except Exception as e:
        _ping("fail")
        raise

    _ping()  # success
    print(f"\n{'='*60}")
    print("Pipeline complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
