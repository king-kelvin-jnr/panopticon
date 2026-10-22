"""Defensive actions mapped to explainable risk-engine findings."""

from __future__ import annotations


def recommend_countermeasures(findings: list[dict]) -> list[dict]:
    """Convert observed findings into deduplicated, actionable defensive steps."""
    recommendations: list[dict] = []
    seen: set[str] = set()

    for finding in findings:
        action = str(finding.get("defensive_response", "")).strip()
        if not action:
            continue
        key = action.casefold()
        if key in seen:
            continue
        seen.add(key)
        recommendations.append(
            {
                "priority": "High" if finding.get("severity") == "High" else "Standard",
                "action": action,
                "reason": f"Responds to: {finding.get('category', 'identified signal')}.",
                "related_category": finding.get("category", "Unknown"),
            }
        )

    if not recommendations:
        recommendations.extend(
            [
                {
                    "priority": "Standard",
                    "action": "Verify material claims using at least one independent source.",
                    "reason": "The rule engine did not identify a predefined signal; that does not establish safety.",
                    "related_category": "Baseline safeguard",
                },
                {
                    "priority": "Standard",
                    "action": "Separate observable facts, assumptions, and emotional framing before deciding.",
                    "reason": "A simple evidence check can expose missing context even when phrase rules do not match.",
                    "related_category": "Baseline safeguard",
                },
            ]
        )

    return recommendations
