"""Scrape Ashby ATS job boards via the official posting API (no Playwright needed).

API: https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true
Returns full job data including description — skips Phase 3 enrichment for these jobs.
"""
import json
import re
import urllib.request
from html.parser import HTMLParser
from playwright.sync_api import Browser


class _StripHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []
    def handle_data(self, data):
        self._parts.append(data)
    def get_text(self):
        return " ".join(self._parts).strip()


def _strip_html(html: str) -> str:
    if not html:
        return ""
    p = _StripHTML()
    p.feed(html)
    text = p.get_text()
    return re.sub(r"\s+", " ", text).strip()


def _slug_from_url(url: str) -> str:
    """Extract board slug from jobs.ashbyhq.com/{slug} or embedded ashby URLs."""
    url = url.rstrip("/")
    # jobs.ashbyhq.com/{slug}
    if "ashbyhq.com" in url:
        return url.split("/")[-1].split("?")[0].split("#")[0]
    # Embedded ashby on company site — try to find slug in URL path
    # e.g. company.com/careers#ashby_embed — no slug available, fall back
    return None


def scrape(browser: Browser, source: dict) -> list[dict]:
    url  = source["url"]
    name = source["name"]

    slug = _slug_from_url(url)
    if not slug:
        print(f"    Ashby error ({name}): cannot extract slug from {url}")
        return []

    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    Ashby error ({name}): {e}")
        return []

    postings = data.get("jobs", [])
    jobs = []
    for p in postings:
        job_id = p.get("id", "")
        title  = (p.get("title") or "").strip()
        if not title or not job_id:
            continue

        # Location
        location = p.get("locationName") or ""
        if p.get("isRemote") and "remote" not in location.lower():
            location = f"Remote{' — ' + location if location else ''}"

        # Salary
        comp     = p.get("compensation") or {}
        sal_min  = comp.get("minValue")
        sal_max  = comp.get("maxValue")
        currency = comp.get("currency", "USD")

        # Date
        date_posted = (p.get("publishedDate") or "")[:10] or None

        # Description — strip HTML so Phase 3 can be skipped
        description = _strip_html(p.get("descriptionHtml") or "")

        jobs.append({
            "title":       title,
            "company":     name,
            "location":    location,
            "url":         f"https://jobs.ashbyhq.com/{slug}/{job_id}",
            "source":      "ashby",
            "department":  p.get("teamName") or None,
            "salary_min":  int(sal_min) if sal_min else None,
            "salary_max":  int(sal_max) if sal_max else None,
            "salary_currency": currency,
            "date_posted": date_posted,
            "description": description or None,
        })

    print(f"    {name}: {len(jobs)} jobs")
    return jobs
