import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from unittest.mock import patch, MagicMock
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


def test_score_job_returns_score_and_reasoning():
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text='{"score": 8.5, "reasoning": "Strong fit: CS leadership from scratch at an AI startup matches profile exactly."}')
    ]

    with patch("pipeline.scorer.anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_response

        score, reasoning = score_job("Head of Customer Success", "Acme AI", SAMPLE_JD)

    assert score == 8.5
    assert "CS leadership" in reasoning


def test_score_job_handles_bad_json():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Sorry, I can't score this.")]

    with patch("pipeline.scorer.anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_response

        score, reasoning = score_job("Head of Customer Success", "Acme AI", SAMPLE_JD)

    assert score == 0.0
    assert reasoning == ""


def test_score_job_strips_markdown_fences():
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text='```json\n{"score": 7.0, "reasoning": "Good match."}\n```')
    ]

    with patch("pipeline.scorer.anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_response

        score, reasoning = score_job("VP Customer Experience", "Some Co", SAMPLE_JD)

    assert score == 7.0
    assert reasoning == "Good match."


def test_score_is_rounded_to_one_decimal():
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text='{"score": 6.666, "reasoning": "Decent fit."}')
    ]

    with patch("pipeline.scorer.anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_response

        score, _ = score_job("Support Director", "Some Co", SAMPLE_JD)

    assert score == 6.7
