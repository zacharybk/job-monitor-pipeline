"""Score a job against the user profile.

Prefers DigitalOcean Gradient serverless inference (OpenAI-compatible, billed to
DO credits); falls back to Anthropic direct when DO_INFERENCE_KEY is unset.
"""
import json
import re
import unicodedata
from typing import Optional

from pipeline import config


def _sanitize(text: str) -> str:
    """Normalize unicode to ASCII-safe text (handles em dashes, curly quotes, etc.)."""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')


_SYSTEM_PROMPT = (
    "You are a job-fit evaluator. Given a job description and a candidate profile, "
    "return a JSON object with exactly two keys:\n"
    '- "score": a number from 0.0 to 10.0 (10 = perfect fit, 0 = completely irrelevant)\n'
    '- "reasoning": one sentence explaining the score\n\n'
    "Only return valid JSON. No markdown, no extra text."
)

_USER_TEMPLATE = """## Candidate Profile
{profile}

## Job: {title} at {company}
{description}

Return JSON only."""


def _build_prompt(title: str, company: str, description: str) -> str:
    return _USER_TEMPLATE.format(
        profile=_sanitize(config.PROFILE_TEXT[:3000]),
        title=_sanitize(title),
        company=_sanitize(company),
        description=_sanitize(description[:4000]),
    )


def _parse(raw: str) -> tuple[float, str]:
    """Parse the model's JSON reply into (score, reasoning). Raises on bad JSON."""
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL).strip()
    data = json.loads(raw)
    score = round(float(data["score"]), 1)
    reasoning = str(data.get("reasoning", ""))
    return score, reasoning


def score_job(title: str, company: str, description: str) -> Optional[tuple[float, str]]:
    """Score a job 0.0–10.0 against PROFILE_TEXT.

    Returns (score, reasoning), or None on any failure so the caller can skip and
    retry the job on a later run — never a fake 0.0 that a later reader would
    mistake for a real "irrelevant" score.
    """
    prompt = _build_prompt(title, company, description)

    try:
        if config.DO_INFERENCE_KEY:
            from openai import OpenAI
            client = OpenAI(
                api_key=config.DO_INFERENCE_KEY,
                base_url=config.DO_INFERENCE_BASE_URL,
            )
            response = client.chat.completions.create(
                model=config.DO_SCORING_MODEL,
                max_tokens=200,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = response.choices[0].message.content

        elif config.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=config.SCORING_MODEL,
                max_tokens=200,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text

        else:
            raise RuntimeError(
                "No scoring backend configured: set DO_INFERENCE_KEY or ANTHROPIC_API_KEY"
            )

        return _parse(raw)

    except Exception as e:
        print(f"    Scorer error for '{title}' at '{company}': {e}")
        return None
