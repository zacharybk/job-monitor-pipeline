"""Scrape VC job boards on the Consider platform (a16z, Sequoia, etc.)."""
from playwright.sync_api import Browser


def scrape(browser: Browser, source: dict) -> list[dict]:
    url  = source["url"]
    name = source["name"]
    jobs = []
    page = browser.new_page()
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)

        seen_urls: set[str] = set()

        # Grouped layout (e.g. Sequoia): jobs nested under company group
        grouped = page.query_selector_all(".grouped-job-result")
        if grouped:
            for group in grouped:
                company = name
                header  = group.query_selector(".grouped-job-result-header a")
                if header:
                    company = header.inner_text().strip() or name
                    if not company:
                        img = header.query_selector("img")
                        if img:
                            company = (img.get_attribute("alt") or "").replace(" logo", "").strip()
                for card in group.query_selector_all(".job-list-job"):
                    job = _extract_card(card, company, seen_urls)
                    if job:
                        jobs.append(job)
        else:
            # Flat layout (e.g. a16z): each card has its own company link
            for card in page.query_selector_all(".job-list-job"):
                company_el = card.query_selector(".job-list-job-company-link")
                company    = company_el.inner_text().strip() if company_el else name
                job = _extract_card(card, company, seen_urls)
                if job:
                    jobs.append(job)

    except Exception as e:
        print(f"    VC board error ({name}): {e}")
    finally:
        page.close()
    print(f"    {name}: {len(jobs)} jobs")
    return jobs


def _extract_card(card, company: str, seen_urls: set) -> dict | None:
    try:
        title_el = card.query_selector("h2.job-list-job-title a")
        if not title_el:
            return None
        title = title_el.inner_text().strip()
        url   = title_el.get_attribute("href") or ""
        if not title or not url or url in seen_urls:
            return None
        seen_urls.add(url)
        parts     = []
        remote_el = card.query_selector(".job-list-badge-remote")
        if remote_el:
            parts.append(remote_el.inner_text().strip())
        loc_el = card.query_selector(".job-list-badge-locations")
        if loc_el:
            parts.append(loc_el.inner_text().strip())
        return {
            "title":    title,
            "company":  company,
            "location": " - ".join(p for p in parts if p),
            "url":      url,
            "source":   "vc_job_board",
        }
    except Exception:
        return None
