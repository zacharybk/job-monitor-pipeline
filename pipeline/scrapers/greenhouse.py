"""Scrape Greenhouse job boards via the public API (no Playwright needed)."""
import json
import urllib.request
from playwright.sync_api import Browser


def scrape(browser: Browser, source: dict) -> list[dict]:
    """
    Calls the Greenhouse Job Board API directly.
    URL format: https://job-boards.greenhouse.io/{token}
    API format: https://boards-api.greenhouse.io/v1/boards/{token}/jobs
    """
    url   = source["url"].rstrip("/")
    name  = source["name"]
    token = url.split("/")[-1]
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    Greenhouse error ({name}): {e}")
        return []

    jobs = []
    for job in data.get("jobs", []):
        jobs.append({
            "title":       job.get("title", "").strip(),
            "company":     name,
            "location":    job.get("location", {}).get("name", ""),
            "url":         job.get("absolute_url", ""),
            "source":      "greenhouse",
            "date_posted": (job.get("first_published") or "")[:10] or None,
        })

    print(f"    {name}: {len(jobs)} jobs")
    return [j for j in jobs if j["url"]]
