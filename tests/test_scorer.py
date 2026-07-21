import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from unittest.mock import patch, MagicMock
import pytest
from pipeline import config
from pipeline.scorer import score_job

SAMPLE_JD = """
Head of Customer Success at Acme AI
Location: Remote, US
We are looking for a Head of Customer Success to build and lead our CS function from scratch.
You will own onboarding, retention, and expansion for our mid-market and enterprise customers.
Requirements: 8+ years in customer success or support leadership, experience at a SaaS startup,
ability to hire and develop a team. Familiarity with AI tools a plus.
Compensation: $160,000-$180,000 + equity
"""


@pytest.fixture
def anthropic_backend(monkeypatch):
    """Force the Anthropic code path (no DO key) so we can mock the SDK."""
    monkeypatch.setattr(config, "DO_INFERENCE_KEY", "")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")


def _mock_anthropic(text):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=text)]
    MockClient = MagicMock()
    MockClient.return_value.messages.create.return_value = mock_response
    return MockClient


def test_score_job_returns_score_and_reasoning(anthropic_backend):
    MockClient = _mock_anthropic(
        '{"score": 8.5, "reasoning": "Strong fit: CS leadership from scratch at an AI startup."}')
    with patch("anthropic.Anthropic", MockClient):
        result = score_job("Head of Customer Success", "Acme AI", SAMPLE_JD)
    assert result is not None
    score, reasoning = result
    assert score == 8.5
    assert "CS leadership" in reasoning


def test_score_job_returns_none_on_bad_json(anthropic_backend):
    MockClient = _mock_anthropic("Sorry, I can't score this.")
    with patch("anthropic.Anthropic", MockClient):
        result = score_job("Head of Customer Success", "Acme AI", SAMPLE_JD)
    assert result is None  # failure must not masquerade as a real 0.0 score


def test_score_job_strips_markdown_fences(anthropic_backend):
    MockClient = _mock_anthropic('```json\n{"score": 7.0, "reasoning": "Good match."}\n```')
    with patch("anthropic.Anthropic", MockClient):
        result = score_job("VP Customer Experience", "Some Co", SAMPLE_JD)
    assert result == (7.0, "Good match.")


def test_score_is_rounded_to_one_decimal(anthropic_backend):
    MockClient = _mock_anthropic('{"score": 6.666, "reasoning": "Decent fit."}')
    with patch("anthropic.Anthropic", MockClient):
        result = score_job("Support Director", "Some Co", SAMPLE_JD)
    assert result is not None
    assert result[0] == 6.7
