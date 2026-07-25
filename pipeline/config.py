"""Central config: environment, profile text, filter lists."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# ── RapidAPI ──────────────────────────────────────────────────────────────────
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")  # required for yc_api source

# ── Scoring backend ───────────────────────────────────────────────────────────
# Preferred: DigitalOcean Gradient serverless inference (OpenAI-compatible, billed
# to DO credits, same Haiku pricing). Create a model access key in the DO console
# (Inference → model access keys) and set DO_INFERENCE_KEY in .env.
# Scoring is the gate that decides what Zach sees, so we use Sonnet (better judgment)
# rather than Haiku. Confirm the exact model slug against your account with:
#   curl -s https://inference.do-ai.run/v1/models \
#     -H "Authorization: Bearer $DO_INFERENCE_KEY" | python3 -m json.tool
# then set DO_SCORING_MODEL in .env to the Sonnet 5 slug it lists.
DO_INFERENCE_KEY      = os.getenv("DO_INFERENCE_KEY", "")
DO_INFERENCE_BASE_URL = os.getenv("DO_INFERENCE_BASE_URL", "https://inference.do-ai.run/v1")
DO_SCORING_MODEL      = os.getenv("DO_SCORING_MODEL", "anthropic-claude-4.6-sonnet")

# Fallback: Anthropic direct (used only when DO_INFERENCE_KEY is unset).
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SCORING_MODEL     = "claude-haiku-4-5-20251001"

# ── Healthchecks.io ───────────────────────────────────────────────────────────
HEALTHCHECK_URL = os.getenv("HEALTHCHECK_URL", "")  # optional

# ── Pipeline tuning ───────────────────────────────────────────────────────────
MAX_SCRAPE_WORKERS = 2    # parallel Playwright browsers
ENRICH_BATCH_SIZE  = 100  # jobs to enrich per run
SCORE_BATCH_SIZE   = 100  # jobs to score per run
MIN_MATCH_SCORE    = 5.0  # 0–10; used for display filtering

# ── Profile ───────────────────────────────────────────────────────────────────
# Copy profile.example.md to profile.md and fill in your background.
# This is what Claude Haiku scores jobs against — be specific.
_PROFILE_PATH = Path(__file__).parent.parent / "profile.md"
_EXAMPLE_PATH = Path(__file__).parent.parent / "profile.example.md"
if _PROFILE_PATH.exists():
    PROFILE_TEXT = _PROFILE_PATH.read_text()
elif _EXAMPLE_PATH.exists():
    # Never let a missing personal profile crash the whole pipeline (scraping does
    # not need it; only scoring does). Fall back so scraping keeps running.
    import warnings
    warnings.warn("profile.md not found; falling back to profile.example.md. "
                  "Scoring will be inaccurate until profile.md is restored.")
    PROFILE_TEXT = _EXAMPLE_PATH.read_text()
else:
    PROFILE_TEXT = ""  # scraping still runs; scoring is skipped/degraded

# ── Relevance pre-filter ──────────────────────────────────────────────────────
# Jobs must contain at least one INCLUDE keyword and zero EXCLUDE keywords.
# Only relevant jobs get enriched (JD fetched) and scored (Haiku API called).

INCLUDE_TITLE_KEYWORDS = [
    "customer",
    "support",
    "success",
    " cx",   # matches "VP of CX", "Head of CX"
    "cx ",   # matches "CX Manager", "CX Director"
    "cx,",
    "cx-",
    "service",
    "experience",
    "operations",
    "account management",
    "head of experience",
    "client",
]

EXCLUDE_TITLE_KEYWORDS = [
    "software engineer",
    "engineering",
    "product manager",
    "product design",
    "marketing",
    "sales development",
    "sdr",
    "bdr",
    "data scientist",
    "data engineer",
    "machine learning",
    "devops",
    "security engineer",
    "finance",
    "accounting",
    "legal",
    "recruiter",
    "talent acquisition",
    "people ops",
    "human resources",
    "hr ",
    "employee experience",
    "graphic design",
    "content writer",
    "seo",
    "paid media",
]

# Positive US location signals
US_LOCATION_KEYWORDS = [
    "usa",
    "united states",
    "u.s.",
    "remote - us",
    "remote (us",
    "remote, us",
    "remote — us",
    "new york",
    "san francisco",
    "california",
    "texas",
    "boston",
    "seattle",
    "chicago",
    "denver",
    "austin",
]

# Non-US signals — exclude if found without a US signal
NON_US_LOCATION_KEYWORDS = [
    "uk",
    "united kingdom",
    "london",
    "europe",
    "eu",
    "germany",
    "berlin",
    "canada",
    "toronto",
    "vancouver",
    "australia",
    "sydney",
    "india",
    "apac",
    "asia",
    "latam",
    "mexico",
    "brazil",
    "france",
    "paris",
    "ireland",
    "dublin",
    "netherlands",
    "amsterdam",
]
