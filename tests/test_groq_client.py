from dataclasses import replace

import pytest

from panopticon.config import Settings
from panopticon.groq_client import GroqClient, GroqError


def base_settings(api_key="test-groq-key"):
    return Settings(
        qloo_api_key=None,
        qloo_api_url="https://api.qloo.com/v2/insights",
        groq_api_key=api_key,
        groq_model="openai/gpt-oss-120b",
        groq_api_url="https://api.groq.com/openai/v1/chat/completions",
        request_timeout=3,
    )


def test_missing_groq_key_is_explicit():
    with pytest.raises(GroqError, match="GROQ_API_KEY is not configured"):
        GroqClient(base_settings(None)).generate_synthetic_scenario("invoice fraud training")


def test_invalid_summary_json_is_rejected(monkeypatch):
    client = GroqClient(base_settings())
    monkeypatch.setattr(client, "_chat", lambda *args, **kwargs: "not json")
    with pytest.raises(GroqError, match="not valid JSON"):
        client.create_analysis_summary(
            "Synthetic example: A fictional supplier requests payment today.", [], None
        )


def test_summary_rejects_missing_required_fields(monkeypatch):
    client = GroqClient(base_settings())
    monkeypatch.setattr(client, "_chat", lambda *args, **kwargs: '{"summary": "only a summary"}')
    with pytest.raises(GroqError, match="missing required text fields"):
        client.create_analysis_summary(
            "Synthetic example: A fictional supplier requests payment today.", [], None
        )
