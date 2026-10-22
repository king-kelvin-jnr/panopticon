import pytest

from panopticon.risk_engine import (
    ScenarioValidationError,
    analyze_scenario,
    validate_scenario,
)
from panopticon.countermeasures import recommend_countermeasures


def test_detects_urgency_and_suppression_with_exact_evidence():
    scenario = (
        "Synthetic example: A fictional vendor says the payment expires today. "
        "Act now and don't tell anyone or the contract will be lost."
    )
    result = analyze_scenario(scenario)
    by_id = {finding["rule_id"]: finding for finding in result["findings"]}

    assert "urgency_pressure" in by_id
    assert "expires today" in by_id["urgency_pressure"]["evidence"]
    assert "verification_suppression" in by_id
    assert "don't tell anyone" in by_id["verification_suppression"]["evidence"]
    assert result["matched_categories"] == 2


def test_does_not_claim_scenario_is_safe_when_no_rule_matches():
    result = analyze_scenario(
        "Synthetic example: The team reviews a proposed meeting agenda on Friday afternoon."
    )
    assert result["findings"] == []
    assert "not proof of safety" in result["assessment_note"]


def test_countermeasure_engine_provides_baseline_safeguards_when_no_findings():
    actions = recommend_countermeasures([])
    assert len(actions) >= 2
    assert any("independent source" in item["action"] for item in actions)


def test_empty_or_short_scenario_is_rejected():
    with pytest.raises(ScenarioValidationError):
        validate_scenario("too short")


def test_overlong_scenario_is_rejected():
    with pytest.raises(ScenarioValidationError):
        validate_scenario("x" * 6001)
