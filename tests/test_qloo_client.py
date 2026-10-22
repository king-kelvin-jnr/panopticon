from dataclasses import replace

import pytest
import requests

from panopticon.config import Settings
from panopticon.qloo_client import QlooClient, QlooError, parse_entity_urns


class FakeResponse:
    def __init__(self, status_code=200, payload=None, invalid_json=False):
        self.status_code = status_code
        self.payload = payload
        self.invalid_json = invalid_json

    def json(self):
        if self.invalid_json:
            raise ValueError("not json")
        return self.payload


def base_settings():
    return Settings(
        qloo_api_key="test-qloo-key",
        qloo_api_url="https://api.qloo.com/v2/insights",
        groq_api_key=None,
        groq_model="openai/gpt-oss-120b",
        groq_api_url="https://api.groq.com/openai/v1/chat/completions",
        request_timeout=3,
    )


def test_parses_and_deduplicates_entity_urns():
    result = parse_entity_urns(
        "urn:entity:artist:brian-eno, urn:entity:brand:jil-sander, urn:entity:artist:brian-eno"
    )
    assert result == ["urn:entity:artist:brian-eno", "urn:entity:brand:jil-sander"]


def test_rejects_invalid_entity_urn():
    with pytest.raises(QlooError):
        parse_entity_urns("brian eno")


def test_qloo_call_uses_documented_route_auth_and_params(monkeypatch):
    seen = {}

    def fake_get(url, *, headers, params, timeout):
        seen.update(url=url, headers=headers, params=params, timeout=timeout)
        return FakeResponse(payload={"results": [{"tag": "ambient & modern-classical", "affinity": 0.89}]})

    monkeypatch.setattr("panopticon.qloo_client.requests.get", fake_get)
    result = QlooClient(base_settings()).get_cultural_tags("urn:entity:artist:brian-eno")

    assert seen["url"] == "https://api.qloo.com/v2/insights"
    assert seen["headers"]["x-api-key"] == "test-qloo-key"
    assert seen["params"]["filter.type"] == "urn:tag"
    assert seen["params"]["signal.interests.entities"] == "urn:entity:artist:brian-eno"
    assert seen["params"]["take"] == 6
    assert result["status"] == "live_success"
    assert result["result_count"] == 1
    assert result["items"][0]["tag"] == "ambient & modern-classical"
    assert result["items"][0]["affinity"] == 0.89


def test_missing_qloo_key_is_reported_without_network_call(monkeypatch):
    settings = replace(base_settings(), qloo_api_key=None)
    monkeypatch.setattr(
        "panopticon.qloo_client.requests.get",
        lambda *args, **kwargs: pytest.fail("Network call must not occur without key"),
    )
    with pytest.raises(QlooError, match="QLOO_API_KEY is not configured"):
        QlooClient(settings).get_cultural_tags("urn:entity:artist:brian-eno")


def test_authentication_error_is_sanitized(monkeypatch):
    monkeypatch.setattr(
        "panopticon.qloo_client.requests.get",
        lambda *args, **kwargs: FakeResponse(status_code=401, payload={"detail": "private service text"}),
    )
    with pytest.raises(QlooError) as error:
        QlooClient(base_settings()).get_cultural_tags("urn:entity:artist:brian-eno")
    assert error.value.status_code == 401
    assert "private service text" not in error.value.public_message
    assert "authentication" in error.value.public_message


def test_timeout_is_handled(monkeypatch):
    def timeout(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr("panopticon.qloo_client.requests.get", timeout)
    with pytest.raises(QlooError, match="timed out"):
        QlooClient(base_settings()).get_cultural_tags("urn:entity:artist:brian-eno")


def test_unexpected_json_shape_is_not_fabricated(monkeypatch):
    monkeypatch.setattr(
        "panopticon.qloo_client.requests.get",
        lambda *args, **kwargs: FakeResponse(payload={"results": {"unexpected": "shape"}}),
    )
    with pytest.raises(QlooError, match="unexpected 'results' format"):
        QlooClient(base_settings()).get_cultural_tags("urn:entity:artist:brian-eno")
