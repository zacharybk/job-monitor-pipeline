"""Scrape generic company career pages."""
from urllib.parse import urljoin
from playwright.sync_api import Browser

_SKIP_TITLES = {"apply", "view all", "see all", "back", "home", "learn more", "read more"}


def scrape(browser: Browser, source: dict) -> list[dict]:
    url  = source["url"]
    name = source["name"]
    jobs = []
    page = browser.new_page()
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        links = page.query_selector_all(
            "a[href*='job'], a[href*='position'], a[href*='career'], "
            "a[href*='opening'], a[href*='role'], a[href*='apply'], "
            "[class*='job'] a, [class*='position'] a, [class*='opening'] a"
        )
        seen: set[str] = set()
        for link in links:
            try:
                href = link.get_attribute("href")
                if not href or href in seen:
                    continue
                seen.add(href)
                if href.startswith("/"):
                    href = urljoin(url, href)
                title = link.inner_text().strip()
                if not title or len(title) < 5 or len(title) > 100:
                    continue
                if any(skip in title.lower() for skip in _SKIP_TITLES):
                    continue
                jobs.append({"title": title, "company": name,
                             "location": "", "url": href, "source": "career_page"})
            except Exception:
                continue
    except Exception as e:
        print(f"    Career page error ({name}): {e}")
    finally:
        page.close()
    print(f"    {name}: {len(jobs)} jobs")
    return jobs
