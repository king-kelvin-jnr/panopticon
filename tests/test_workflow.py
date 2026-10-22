from dataclasses import replace

from panopticon.config import Settings
from panopticon.workflow import PanopticonAgent


def settings(qloo_api_key=None, groq_api_key=None):
    return Settings(
        qloo_api_key=qloo_api_key,
        qloo_api_url="https://api.qloo.com/v2/insights",
        groq_api_key=groq_api_key,
        groq_model="openai/gpt-oss-120b",
        groq_api_url="https://api.groq.com/openai/v1/chat/completions",
        request_timeout=3,
    )


def test_workflow_runs_without_credentials_and_does_not_fabricate_provider_data():
    agent = PanopticonAgent(settings())
    report = agent.analyze(
        "Synthetic example: The fictional sender says the payment expires today. "
        "Act now and don't tell anyone."
    )

    assert report["risk_report"]["matched_categories"] >= 2
    assert report["qloo_context"]["status"] == "not_requested"
    assert report["qloo_context"]["items"] == []
    assert report["llm_status"] == "not_configured"
    assert report["llm_summary"] is None
    assert len(report["countermeasures"]) >= 2
    assert all(step["status"] for step in report["workflow_steps"])


def test_workflow_never_calls_qloo_without_key(monkeypatch):
    agent = PanopticonAgent(settings(qloo_api_key=None))
    monkeypatch.setattr(
        agent.qloo_client,
        "get_cultural_tags",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not call Qloo without key")),
    )
    report = agent.analyze(
        "Synthetic example: A fictional supplier asks an employee to transfer funds. "
        "Act now before the payment expires today.",
        "urn:entity:artist:brian-eno",
    )
    assert report["qloo_context"]["status"] == "not_configured"
    assert report["qloo_context"]["raw_response"] is None
