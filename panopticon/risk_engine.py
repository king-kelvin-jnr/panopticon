"""PANOPTICON explainable cognitive-risk analysis engine.

Findings are based on explicit wording in the supplied message.
A phrase match is not proof of deception, intent, or harm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern

MAX_SCENARIO_CHARS = 6_000
MIN_SCENARIO_CHARS = 20


@dataclass(frozen=True)
class RiskRule:
    """A deterministic rule with inspectable evidence."""

    rule_id: str
    category: str
    pattern: Pattern[str]
    severity: str
    explanation: str
    defensive_response: str


RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id="urgency_pressure",
        category="Urgency and deadline pressure",
        pattern=re.compile(
            r"\b(?:"
            r"urgent(?:ly)?|immediately|right away|right now|act now|respond now|"
            r"last chance|time[- ]sensitive|don't delay|do not delay|"
            r"expires? today|today only|before midnight|"
            r"within\s+(?:(?:the|next)\s+){0,2}\d+\s+"
            r"(?:minutes?|hours?|days?)|"
            r"in\s+(?:the\s+)?next\s+\d+\s+(?:minutes?|hours?|days?)"
            r")\b",
            re.IGNORECASE,
        ),
        severity="Moderate",
        explanation=(
            "The wording emphasizes urgency or a short deadline. "
            "A real deadline may exist; the wording alone cannot establish "
            "whether it is legitimate."
        ),
        defensive_response=(
            "Pause. Independently confirm the deadline and its consequences "
            "through a trusted channel before acting."
        ),
    ),
    RiskRule(
        rule_id="verification_suppression",
        category="Suppression of independent verification",
        pattern=re.compile(
            r"\b(?:"
            r"don't tell anyone|do not tell anyone|"
            r"keep (?:this|it) secret|keep this confidential|"
            r"don't verify|do not verify|don't check|do not check|"
            r"don't ask questions|do not ask questions|"
            r"no need to verify|don't look it up|do not look it up|"
            r"don't contact (?:the bank|support|your manager|the office|finance|procurement)|"
            r"do not contact (?:the bank|support|your manager|the office|finance|procurement)|"
            r"ignore anyone who questions|"
            r"without (?:independent )?verification"
            r")\b",
            re.IGNORECASE,
        ),
        severity="High",
        explanation=(
            "The message discourages disclosure, questioning, or independent "
            "verification. This warrants review but does not independently "
            "prove deceptive intent."
        ),
        defensive_response=(
            "Maintain normal checks. Verify the request using independently "
            "obtained contact details and involve an authorized reviewer."
        ),
    ),
    RiskRule(
        rule_id="process_bypass",
        category="Request to bypass established controls",
        pattern=re.compile(
            r"\b(?:"
            r"(?:override|bypass|circumvent|skip|waive|ignore)\b"
            r"[^.!?\n]{0,100}\b"
            r"(?:review\s+window|review\s+period|review|approval\s+process|"
            r"approval|verification|controls?|safeguards?|standard\s+process|"
            r"normal\s+process|usual\s+process|procedures?)"
            r"|"
            r"(?:outside|without|instead\s+of)\s+(?:the\s+)?"
            r"(?:normal|standard|usual|required)\s+"
            r"(?:\d+[- ]?hour\s+)?"
            r"(?:review\s+window|review\s+period|approval\s+process|procedure)"
            r"|"
            r"(?:bypass|skip|override)\s+(?:the\s+)?"
            r"(?:normal|standard|usual|required)\s+"
            r"(?:approval|review|verification|payment)\s+"
            r"(?:process|steps?|controls?)"
            r")\b",
            re.IGNORECASE,
        ),
        severity="High",
        explanation=(
            "The wording explicitly requests an exception to an established "
            "review, approval, or verification process."
        ),
        defensive_response=(
            "Do not bypass required controls based on this message. Follow "
            "the documented approval process and escalate any claimed "
            "exception to an authorized reviewer."
        ),
    ),
    RiskRule(
        rule_id="consequence_threat",
        category="Threatened financial or contractual consequences",
        pattern=re.compile(
            r"\b(?:"
            r"(?:significant|substantial|major|heavy|severe|financial|contractual)\s+"
            r"penalt(?:y|ies)|"
            r"breach(?:ing)?\s+(?:the\s+)?(?:sla|contract|agreement)|"
            r"service interruption|"
            r"(?:shipments?|operations?)\s+(?:will\s+be\s+)?"
            r"(?:frozen|blocked|stopped)|"
            r"ability to ship\s+[^.!?\n]{0,60}\s+"
            r"(?:frozen|blocked|stopped)"
            r")\b",
            re.IGNORECASE,
        ),
        severity="Moderate",
        explanation=(
            "The text refers to specific financial, service, or contractual "
            "consequences. Verify those claims independently rather than "
            "assuming they are either true or false."
        ),
        defensive_response=(
            "Request verifiable evidence of the claimed consequences and "
            "check them with the contract owner or another trusted source."
        ),
    ),
    RiskRule(
        rule_id="authority_approval_claim",
        category="Unverified authority or approval claim",
        pattern=re.compile(
            r"\b(?:"
            r"(?:finance director|director|executive|manager|regulator|"
            r"authority)\s+(?:has\s+)?(?:already\s+)?"
            r"(?:approved|authorized|required|ordered|confirmed)\s+"
            r"(?:the\s+)?(?:payment|transfer|request|exception|action)|"
            r"(?:approved|authorized)\s+by\s+(?:the\s+)?"
            r"(?:finance director|director|executive|regulator|authority)|"
            r"(?:finance director|director|executive)\s+"
            r"already\s+approved"
            r")\b",
            re.IGNORECASE,
        ),
        severity="Moderate",
        explanation=(
            "The wording invokes a claimed authorization by a person or "
            "authority. The claim needs independent confirmation."
        ),
        defensive_response=(
            "Confirm the authorization directly with the named internal "
            "approver using contact details already on file."
        ),
    ),
    RiskRule(
        rule_id="commitment_pressure",
        category="Pressure for an immediate commitment",
        pattern=re.compile(
            r"\b(?:"
            r"please\s+reply\s+yes|reply\s+yes|respond\s+yes|"
            r"reply\s+with\s+(?:yes|approved)|"
            r"confirm\s+(?:immediately|right away|now)|"
            r"give\s+(?:the\s+)?go[- ]ahead|"
            r"give\s+(?:me\s+)?(?:your\s+)?approval\s+now"
            r")\b",
            re.IGNORECASE,
        ),
        severity="Moderate",
        explanation=(
            "The message requests a quick commitment that could be mistaken "
            "for approval. A short reply should not replace formal controls."
        ),
        defensive_response=(
            "Use the documented approval system and record who authorized "
            "the action, rather than relying on a short message reply."
        ),
    ),
    RiskRule(
        rule_id="specific_financial_details",
        category="Specific financial details present",
        pattern=re.compile(
            r"\b(?:"
            r"(?:USD|EUR|GBP|NGN)\s?\d[\d,]*(?:\.\d{2})?|"
            r"(?:INV|INVOICE)[- #]?[A-Z0-9-]{4,}|"
            r"change\s+(?:the\s+)?(?:bank account|payment details)"
            r")\b",
            re.IGNORECASE,
        ),
        severity="Context flag",
        explanation=(
            "The text contains specific payment or financial details. "
            "This is contextual information, not evidence of manipulation "
            "on its own."
        ),
        defensive_response=(
            "Check invoice identifiers, amounts, and payment details against "
            "independently held records before authorizing funds."
        ),
    ),
    RiskRule(
        rule_id="emotional_pressure",
        category="Emotional pressure",
        pattern=re.compile(
            r"\b(?:"
            r"if you (?:really )?care|prove your loyalty|"
            r"you(?:'|’)ll regret|you will regret|"
            r"don't let (?:me|us|them) down|do not let (?:me|us|them) down|"
            r"you're betraying|you are betraying|betrayal|"
            r"shame on you|feel guilty|disappoint me"
            r")\b",
            re.IGNORECASE,
        ),
        severity="Moderate",
        explanation=(
            "The wording links compliance to guilt, loyalty, shame, or regret "
            "instead of relying solely on verifiable facts."
        ),
        defensive_response=(
            "Separate emotional language from the decision criteria and "
            "request verifiable evidence."
        ),
    ),
    RiskRule(
        rule_id="social_pressure",
        category="Social conformity pressure",
        pattern=re.compile(
            r"\b(?:"
            r"everyone is doing it|everyone agrees|everyone else has|"
            r"all your friends|everybody knows|the whole group expects|"
            r"don't be the only one|do not be the only one|"
            r"you'll be the only one|you will be the only one|"
            r"nobody wants to be left out|millions of people agree"
            r")\b",
            re.IGNORECASE,
        ),
        severity="Low to moderate",
        explanation=(
            "The message appeals to supposed group agreement or fear of "
            "being left out. The claimed consensus may be incomplete."
        ),
        defensive_response=(
            "Ask for independently checkable evidence instead of relying "
            "on popularity or group pressure."
        ),
    ),
    RiskRule(
        rule_id="misleading_framing",
        category="Absolute or restricted framing",
        pattern=re.compile(
            r"\b(?:"
            r"you have only two options|there is no alternative|"
            r"this is the only way|the only possible choice|"
            r"guaranteed to work|100\s*% guaranteed|risk-free|no downside|"
            r"can't possibly fail|cannot possibly fail|everyone wins"
            r")\b",
            re.IGNORECASE,
        ),
        severity="Moderate",
        explanation=(
            "The wording presents an absolute guarantee or restricts the "
            "apparent choices. Check whether alternatives or risks were omitted."
        ),
        defensive_response=(
            "List realistic alternatives and downsides and require evidence "
            "for guarantees."
        ),
    ),
    RiskRule(
        rule_id="uncertainty_exploitation",
        category="Exploitation of uncertainty",
        pattern=re.compile(
            r"\b(?:"
            r"nobody knows|no one knows|we may never know|"
            r"it's impossible to check|it is impossible to check|"
            r"the details are too complicated to explain|"
            r"just take my word for it|"
            r"trust me,?\s+(?:you don't need to know|there is no need to know)"
            r")\b",
            re.IGNORECASE,
        ),
        severity="Moderate",
        explanation=(
            "The wording treats uncertainty as a reason to accept a claim "
            "or stop asking for evidence."
        ),
        defensive_response=(
            "Identify what is known, unknown, and verifiable. Request supporting "
            "evidence and consult an independent source."
        ),
    ),
)


class ScenarioValidationError(ValueError):
    """Raised when scenario input is invalid."""


def validate_scenario(scenario: str) -> str:
    """Validate input type and supported character limits."""

    if not isinstance(scenario, str):
        raise ScenarioValidationError("Scenario must be text.")

    cleaned = scenario.strip()

    if len(cleaned) < MIN_SCENARIO_CHARS:
        raise ScenarioValidationError(
            f"Enter at least {MIN_SCENARIO_CHARS} characters "
            "describing the message or scenario."
        )

    if len(cleaned) > MAX_SCENARIO_CHARS:
        raise ScenarioValidationError(
            f"Message is too long. Maximum length is "
            f"{MAX_SCENARIO_CHARS} characters."
        )

    return cleaned


def _evidence_for_rule(
    text: str,
    rule: RiskRule,
    max_evidence: int = 2,
) -> list[str]:
    """Return up to two distinct exact phrases supporting a rule."""

    evidence: list[str] = []
    seen: set[str] = set()

    for match in rule.pattern.finditer(text):
        phrase = match.group(0).strip()

        if phrase and phrase.casefold() not in seen:
            evidence.append(phrase)
            seen.add(phrase.casefold())

        if len(evidence) >= max_evidence:
            break

    return evidence


def analyze_scenario(scenario: str) -> dict:
    """Analyze wording and return evidence-linked rule findings."""

    text = validate_scenario(scenario)
    findings: list[dict] = []

    for rule in RULES:
        evidence = _evidence_for_rule(text, rule)

        if not evidence:
            continue

        findings.append(
            {
                "rule_id": rule.rule_id,
                "category": rule.category,
                "severity": rule.severity,
                "match_confidence": "High for phrase match",
                "confidence_note": (
                    "A predefined text pattern matched. This is not a probability "
                    "that manipulation occurred or that a participant intended harm."
                ),
                "evidence": evidence,
                "explanation": rule.explanation,
                "defensive_response": rule.defensive_response,
            }
        )

    return {
        "engine": "Panopticon deterministic phrase-rule engine",
        "findings": findings,
        "matched_categories": len(findings),
        "assessment_note": (
            "Rule-based triage only; not scientifically validated. A match is "
            "not proof of manipulation, and no match is not proof of safety. "
            "No match does not establish safety."
        ),
    }