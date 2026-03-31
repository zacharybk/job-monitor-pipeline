"""Score a job against the user profile using Claude Haiku."""
import json
import re
import anthropic
from pipeline.config import ANTHROPIC_API_KEY, SCORING_MODEL, PROFILE_TEXT

_SYSTEM_PROMPT = (
    "You are a job-fit evaluator. Given a job description and a candidate profile, "
    "return a JSON object with exactly two keys:\n"
    '- "score": a float from 0.0 to 10.0 (10 = perfect fit, 0 = completely irrelevant)\n'
    '- "reasoning": one sentence explaining the score\n\n'
    "Only return valid JSON. No markdown, no extra text."
)

_USER_TEMPLATE = """## Candidate Profile
{profile}

## Job: {title} at {company}
{description}

Return JSON only."""


def score_job(title: str, company: str, description: str) -> tuple[float, str]:
    """
    Score a job against PROFILE_TEXT using Claude Haiku.
    Returns (score: float, reasoning: str). Returns (0.0, "") on any failure.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = _USER_TEMPLATE.format(
        profile=PROFILE_TEXT[:3000],      # cap profile length
        title=title,
        company=company,
        description=description[:4000],   # cap JD length
    )

    try:
        response = client.messages.create(
            model=SCORING_MODEL,
            max_tokens=200,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences if model includes them
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()

        data = json.loads(raw)
        score     = round(float(data.get("score", 0.0)), 1)
        reasoning = str(data.get("reasoning", ""))
        return score, reasoning

    except Exception as e:
        print(f"    Scorer error for '{title}' at '{company}': {e}")
        return 0.0, ""
