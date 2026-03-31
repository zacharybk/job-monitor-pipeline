"""Fetch and extract job description text from a job URL."""
from playwright.sync_api import Browser

# Elements to remove before extracting text
_STRIP_SELECTORS = "script, style, nav, header, footer, noscript, svg, img"

# Minimum characters to consider a description useful
_MIN_LENGTH = 200

# Ordered list of selectors to try for JD content (most specific first)
_CONTENT_SELECTORS = [
    "[class*='job-description']",
    "[class*='jobDescription']",
    "[class*='JobDescription']",
    "[id*='job-description']",
    "[id*='jobDescription']",
    "[class*='description']",
    "article",
    "main",
    "body",
]


def fetch_description(browser: Browser, url: str) -> str:
    """
    Navigate to a job URL, extract visible text, return cleaned description.
    Returns empty string if the page fails or content is too short to be useful.
    """
    page = browser.new_page()
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        page.wait_for_timeout(1500)

        # Remove noise elements
        page.evaluate(f"""
            document.querySelectorAll('{_STRIP_SELECTORS}').forEach(el => el.remove())
        """)

        # Try selectors from most to least specific
        text = ""
        for selector in _CONTENT_SELECTORS:
            el = page.query_selector(selector)
            if el:
                candidate = el.inner_text()
                if len(candidate.strip()) >= _MIN_LENGTH:
                    text = candidate
                    break

        return _clean(text)

    except Exception as e:
        print(f"    Enricher error for {url}: {e}")
        return ""
    finally:
        page.close()


def _clean(text: str) -> str:
    """Normalize whitespace and cap length."""
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)[:8000]  # 8k chars is plenty for scoring
