"""Scrape Work at a Startup (YC job board) — workatastartup.com.

NOTE: WAS is a React SPA. The role filter URL params below were inferred
from common YC job board patterns. If results are empty, open
https://www.workatastartup.com/jobs in Chrome DevTools > Network tab,
apply the Operations/Sales filters, and check what query params are used.
Update ROLE_FILTERS accordingly.
"""
from playwright.sync_api import Browser

BASE_URL = "https://www.workatastartup.com"

# "sales" often includes CS/account management at early-stage startups
ROLE_FILTERS = ["operations", "sales"]


def scrape(browser: Browser, source: dict) -> list[dict]:
    jobs: list[dict] = []
    seen_urls: set[str] = set()
    for role in ROLE_FILTERS:
        jobs.extend(_scrape_role(browser, role, seen_urls))
    print(f"    workatastartup.com: {len(jobs)} jobs")
    return jobs


def _scrape_role(browser: Browser, role: str, seen_urls: set) -> list[dict]:
    jobs: list[dict] = []
    page = browser.new_page()
    try:
        url = f"{BASE_URL}/jobs?role={role}&remote=true"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(3000)

        # Scroll to trigger lazy-loaded cards
        for _ in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)

        # YC job cards contain links to individual job pages
        job_links = page.query_selector_all("a[href*='/jobs/']")

        for link in job_links:
            try:
                href = link.get_attribute("href") or ""
                if not href:
                    continue
                if href.startswith("/"):
                    href = f"{BASE_URL}{href}"
                if href in seen_urls:
                    continue

                title = link.inner_text().strip()
                if not title or len(title) < 3 or len(title) > 120:
                    continue

                seen_urls.add(href)

                # Company name: look in the card container
                company  = ""
                location = "Remote"
                try:
                    card = link.evaluate_handle(
                        "el => el.closest('[class*=\"company\"], [class*=\"card\"], "
                        "[class*=\"job\"], li, article') || el.parentElement"
                    )
                    if card:
                        card_el = card.as_element()
                        if card_el:
                            company_el = card_el.query_selector(
                                "[class*='company'], [class*='Company'], [class*='startup-name']"
                            )
                            if company_el:
                                company = company_el.inner_text().strip()
                            loc_el = card_el.query_selector(
                                "[class*='location'], [class*='Location'], [class*='remote']"
                            )
                            if loc_el:
                                location = loc_el.inner_text().strip()
                except Exception:
                    pass

                jobs.append({
                    "title":    title,
                    "company":  company,
                    "location": location,
                    "url":      href,
                    "source":   "workatastartup",
                })
            except Exception:
                continue

    except Exception as e:
        print(f"    workatastartup error (role={role}): {e}")
    finally:
        page.close()
    return jobs
