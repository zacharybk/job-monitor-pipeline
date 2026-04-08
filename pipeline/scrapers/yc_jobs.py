"""Scrape Y Combinator jobs via the RapidAPI free YC jobs endpoint.

Endpoint returns jobs active in the last 7 days.
Pre-filters by CX/ops title keywords and remote=true before they hit phase 2.
"""
import json
import urllib.request
import urllib.parse
from playwright.sync_api import Browser
from pipeline.config import RAPIDAPI_KEY

_ENDPOINT = "https://free-y-combinator-jobs-api.p.rapidapi.com/active-jb-7d"
_TITLE_FILTER = (
    "customer OR support OR success OR operations OR experience OR client"
)
_PAGE_SIZE = 10


def scrape(browser: Browser, source: dict) -> list[dict]:
    name = source["name"]
    jobs = []
    offset = 0

    while True:
        params = urllib.parse.urlencode({
            "title_filter": _TITLE_FILTER,
            "remote":       "true",
            "offset":       offset,
        })
        url = f"{_ENDPOINT}?{params}"
        req = urllib.request.Request(url, headers={
            "x-rapidapi-host": "free-y-combinator-jobs-api.p.rapidapi.com",
            "x-rapidapi-key":  RAPIDAPI_KEY,
            "Content-Type":    "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"    YC Jobs API error (offset={offset}): {e}")
            break

        # API returns a list directly or wrapped in a key
        batch = data if isinstance(data, list) else data.get("jobs", data.get("results", []))
        if not batch:
            break

        for job in batch:
            url_val = (
                job.get("url") or
                job.get("job_url") or
                job.get("link") or
                job.get("apply_url") or ""
            )
            title = (
                job.get("title") or
                job.get("job_title") or ""
            ).strip()
            company = (
                job.get("company_name") or
                job.get("company") or
                job.get("organization") or
                name
            ).strip()
            location = (
                job.get("location") or
                job.get("job_location") or
                "Remote"
            ).strip()
            date_posted = (job.get("date") or job.get("posted_at") or "")[:10] or None

            if url_val and title:
                jobs.append({
                    "title":       title,
                    "company":     company,
                    "location":    location,
                    "url":         url_val,
                    "source":      "yc_api",
                    "date_posted": date_posted,
                })

        if len(batch) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE

    print(f"    {name}: {len(jobs)} jobs")
    return jobs
