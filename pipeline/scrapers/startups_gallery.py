"""Scrape startups.gallery job listings."""
from playwright.sync_api import Browser


def scrape(browser: Browser, source: dict) -> list[dict]:
    jobs = []
    page = browser.new_page()
    try:
        page.goto("https://startups.gallery/jobs?search=customer", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        links = page.query_selector_all(
            "a[href*='/job'], a[href*='greenhouse'], a[href*='lever'], a[href*='ashby']"
        )
        for link in links[:100]:
            try:
                href = link.get_attribute("href")
                if not href or not href.startswith("http"):
                    continue
                text = link.inner_text().strip()
                if not text:
                    continue
                lines   = [l.strip() for l in text.split("\n") if l.strip()]
                title   = lines[0] if lines else ""
                company = location = ""
                if len(lines) >= 2:
                    parts    = lines[1].split(" · ")
                    company  = parts[0].strip() if len(parts) >= 1 else ""
                    location = parts[1].strip() if len(parts) >= 2 else ""
                if not title:
                    continue
                jobs.append({"title": title, "company": company,
                             "location": location, "url": href, "source": "startups_gallery"})
            except Exception:
                continue
    except Exception as e:
        print(f"    startups.gallery error: {e}")
    finally:
        page.close()
    print(f"    startups.gallery: {len(jobs)} jobs")
    return jobs
