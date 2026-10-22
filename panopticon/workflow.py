"""PANOPTICON workflow orchestration.

Connects input validation, explainable risk detection, defensive
countermeasures, Qloo cultural context, and optional Groq reporting.

Submitted content is not automatically classified as real or fictional.
Qloo associations are contextual data, not evidence of individual intent.
"""

from __future__ import annotations

from typing import Any

from .config import Settings, get_settings
from .countermeasures import recommend_countermeasures
from .groq_client import GroqClient, GroqError
from .qloo_client import QlooClient, QlooError, parse_entity_ids
from .risk_engine import analyze_scenario, validate_scenario


CULTURAL_INTERPRETATION_NOTE = (
    "Qloo results are associations returned for the selected cultural "
    "entity identifiers. They do not establish a relationship to the "
    "message unless that relationship is independently demonstrated. "
    "They are not proof of a participant's beliefs, intent, vulnerability, "
    "or susceptibility to manipulation."
)


class PanopticonAgent:
    """Inspectable workflow agent; it takes no autonomous external actions."""

    def __init__(
        self,
        settings: Settings | None = None,
        qloo_client: QlooClient | None = None,
        groq_client: GroqClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.qloo_client = qloo_client or QlooClient(self.settings)
        self.groq_client = groq_client or GroqClient(self.settings)

    def analyze(
        self,
        scenario: str,
        qloo_entity_urns: str | dict[str, Any] = "",
    ) -> dict[str, Any]:
        """Analyze submitted text and report actual provider status.

        `qloo_entity_urns` accepts UUID-style Qloo entity IDs or URNs.
        The previous argument name is retained for compatibility.
        A dictionary may be passed by a caller that has already retrieved
        Qloo context, such as a test or a larger orchestrating workflow.
        """

        cleaned_scenario = validate_scenario(scenario)

        # Step 1: Deterministic findings and defenses do not depend on Qloo.
        risk_report = analyze_scenario(cleaned_scenario)
        countermeasures = recommend_countermeasures(
            risk_report["findings"]
        )

        # Step 2: Establish an explicit default; no API call is implied.
        culture: dict[str, Any] = {
            "status": "not_requested",
            "provider": "Qloo API",
            "endpoint": self.settings.qloo_api_url,
            "input_entity_ids": [],
            "input_entity_urns": [],
            "result_count": 0,
            "items": [],
            "raw_response": None,
            "message": (
                "No Qloo entity IDs or URNs were supplied; "
                "the live Qloo endpoint was not called."
            ),
            "interpretation_note": CULTURAL_INTERPRETATION_NOTE,
        }

        # Accept already-retrieved context for composition and testing.
        # The interactive application passes user-selected IDs as text.
        if isinstance(qloo_entity_urns, dict):
            culture = dict(qloo_entity_urns)
            culture.setdefault("provider", "Qloo API")
            culture.setdefault("endpoint", self.settings.qloo_api_url)
            culture.setdefault("items", [])
            culture.setdefault("result_count", 0)
            culture.setdefault("raw_response", None)
            culture.setdefault(
                "interpretation_note",
                CULTURAL_INTERPRETATION_NOTE,
            )
            culture.setdefault(
                "message",
                "Previously retrieved context was supplied to the workflow.",
            )

        else:
            # Step 3: Validate identifiers before making a live request.
            try:
                entity_ids = parse_entity_ids(qloo_entity_urns)

            except QlooError as exc:
                entity_ids = []
                culture.update(
                    status="invalid_input",
                    message=exc.public_message,
                )

            culture["input_entity_ids"] = entity_ids
            culture["input_entity_urns"] = entity_ids

            if entity_ids:
                if not self.settings.qloo_api_key:
                    culture.update(
                        status="not_configured",
                        message=(
                            "QLOO_API_KEY is not configured; "
                            "no live Qloo request was made."
                        ),
                    )

                else:
                    try:
                        culture = self.qloo_client.get_cultural_tags(
                            entity_ids
                        )

                        culture.setdefault(
                            "input_entity_ids",
                            entity_ids,
                        )
                        culture.setdefault(
                            "input_entity_urns",
                            entity_ids,
                        )
                        culture["interpretation_note"] = (
                            CULTURAL_INTERPRETATION_NOTE
                        )

                        if culture.get("status") == "live_success":
                            culture["message"] = (
                                "A live Qloo Insights request completed. "
                                "Inspect the returned tags and raw response "
                                "to understand exactly what Qloo supplied."
                            )

                    except QlooError as exc:
                        culture.update(
                            status="error",
                            input_entity_ids=entity_ids,
                            input_entity_urns=entity_ids,
                            message=exc.public_message,
                        )

        # Step 4: The language model receives only returned context.
        # It is optional and does not control the deterministic findings.
        llm_summary: dict[str, Any] | None = None
        llm_status = "not_configured"
        llm_message = (
            "GROQ_API_KEY is not configured. The deterministic findings "
            "and countermeasures remain available."
        )

        if self.settings.groq_api_key:
            try:
                llm_summary = self.groq_client.create_analysis_summary(
                    cleaned_scenario,
                    risk_report["findings"],
                    culture,
                )

                llm_status = "success"
                llm_message = (
                    "Groq generated a narrative using the submitted text, "
                    "rule-engine findings, and the supplied Qloo context."
                )

            except GroqError as exc:
                llm_status = "error"
                llm_message = exc.public_message

        # Keep the trace status factual and machine-readable.
        workflow_steps = [
            {
                "step": "Validate submitted text",
                "status": "complete",
            },
            {
                "step": "Run explainable risk rules",
                "status": "complete",
            },
            {
                "step": "Generate defensive countermeasures",
                "status": "complete",
            },
            {
                "step": "Retrieve Qloo cultural context",
                "status": culture.get("status", "unknown"),
            },
            {
                "step": "Generate Groq narrative",
                "status": llm_status,
            },
        ]

        return {
            "scenario": cleaned_scenario,
            "scenario_label": (
                "User-submitted message or scenario "
                "(origin not independently verified)"
            ),
            "scenario_origin": "user_submitted_unverified",
            "risk_report": risk_report,
            "countermeasures": countermeasures,
            "qloo_context": culture,
            "llm_summary": llm_summary,
            "llm_status": llm_status,
            "llm_message": llm_message,
            "workflow_steps": workflow_steps,
            "analysis_limitations": [
                (
                    "Rule-based phrase matches are heuristic signals, "
                    "not scientifically validated probability estimates."
                ),
                (
                    "A finding does not establish deception, intent, "
                    "or that a claim is false."
                ),
                (
                    "Qloo cultural associations do not prove anything "
                    "about a specific participant's beliefs or intent."
                ),
                (
                    "The origin and factual claims of the submitted text "
                    "have not been independently verified by this workflow."
                ),
                (
                    "The Groq narrative is supplementary and may be incomplete. "
                    "Inspect the exact rule evidence and provider response."
                ),
            ],
        }