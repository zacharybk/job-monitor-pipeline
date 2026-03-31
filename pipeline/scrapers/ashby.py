"""Scrape Ashby ATS job boards (jobs.ashbyhq.com)."""
from playwright.sync_api import Browser


def scrape(browser: Browser, source: dict) -> list[dict]:
    """Extract jobs from an Ashby job board using window.__appData."""
    url  = source["url"]
    name = source["name"]
    jobs = []
    page = browser.new_page()
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        app_data = page.evaluate("() => window.__appData")
        if not app_data or "jobBoard" not in app_data:
            return jobs
        postings = app_data["jobBoard"].get("jobPostings", [])
        org_slug = url.rstrip("/").split("/")[-1]
        for p in postings:
            title  = p.get("title", "")
            job_id = p.get("id", "")
            if not title or not job_id:
                continue
            jobs.append({
                "title":    title,
                "company":  name,
                "location": p.get("locationName", ""),
                "url":      f"https://jobs.ashbyhq.com/{org_slug}/{job_id}",
                "source":   "ashby",
            })
    except Exception as e:
        print(f"    Ashby error ({name}): {e}")
    finally:
        page.close()
    print(f"    {name}: {len(jobs)} jobs")
    return jobs
