"""Scrape Greenhouse ATS job boards with pagination support."""
from playwright.sync_api import Browser


def scrape(browser: Browser, source: dict) -> list[dict]:
    url  = source["url"]
    name = source["name"]
    jobs = []
    page = browser.new_page()
    current_page = 1
    try:
        while True:
            paged_url = url if current_page == 1 else f"{url}?page={current_page}"
            page.goto(paged_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)
            elements   = page.query_selector_all(".opening, [class*='job'], a[href*='/jobs/']")
            page_count = 0
            for el in elements:
                try:
                    link = el if el.get_attribute("href") else el.query_selector("a")
                    if not link:
                        continue
                    href = link.get_attribute("href")
                    if not href or "/jobs/" not in href:
                        continue
                    if href.startswith("/"):
                        href = f"https://job-boards.greenhouse.io{href}"
                    title = link.inner_text().strip()
                    if not title or len(title) < 3:
                        continue
                    loc_el   = el.query_selector(".location, [class*='location']")
                    location = loc_el.inner_text().strip() if loc_el else ""
                    jobs.append({"title": title, "company": name,
                                 "location": location, "url": href, "source": "greenhouse"})
                    page_count += 1
                except Exception:
                    continue
            next_link = page.query_selector(f"a[href*='page={current_page + 1}']")
            if next_link and page_count > 0:
                current_page += 1
            else:
                break
    except Exception as e:
        print(f"    Greenhouse error ({name}): {e}")
    finally:
        page.close()
    pages_str = f"{current_page} page{'s' if current_page > 1 else ''}"
    print(f"    {name}: {len(jobs)} jobs ({pages_str})")
    return jobs
