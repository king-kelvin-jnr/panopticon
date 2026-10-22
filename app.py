"""PANOPTICON — Cognitive security and cultural intelligence dashboard."""

from __future__ import annotations

import json
import logging
from typing import Any

import streamlit as st

from panopticon.config import get_settings
from panopticon.groq_client import GroqClient, GroqError
from panopticon.qloo_client import (
    QlooClient,
    QlooError,
    parse_entity_ids,
)
from panopticon.risk_engine import (
    MAX_SCENARIO_CHARS,
    ScenarioValidationError,
)
from panopticon.workflow import PanopticonAgent

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="PANOPTICON | Cognitive Security",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp {
        background: linear-gradient(180deg, #f7faff 0%, #edf4fc 100%);
        color: #14233f;
      }

      [data-testid="stHeader"] {
        background: rgba(247, 250, 255, .94);
      }

      [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #d8e3f1;
      }

      .block-container {
        max-width: 1440px;
        padding-top: 2rem;
        padding-bottom: 3rem;
      }

      .brand-lockup {
        color: #1d4ed8;
        font-size: .78rem;
        font-weight: 800;
        letter-spacing: .19em;
        text-transform: uppercase;
      }

      .hero-title {
        color: #11213d;
        font-size: clamp(2.2rem, 4vw, 3.3rem);
        font-weight: 850;
        line-height: 1.05;
        letter-spacing: -.045em;
        margin: .5rem 0;
      }

      .hero-subtitle {
        max-width: 900px;
        color: #50627c;
        font-size: 1.02rem;
        line-height: 1.65;
      }

      .section-eyebrow {
        color: #2457b8;
        font-size: .75rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
      }

      .section-heading {
        color: #12213d;
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -.02em;
      }

      .section-description {
        color: #5a6b83;
        line-height: 1.55;
      }

      div[data-testid="stForm"],
      div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #d8e3f1;
        border-radius: 16px;
        background: rgba(255,255,255,.96);
      }

      div[data-testid="stMetric"] {
        border: 1px solid #d8e3f1;
        border-radius: 14px;
        background: #ffffff;
        padding: .85rem 1rem;
      }

      div[data-testid="stMetricLabel"] {
        color: #5b6b82;
      }

      div[data-testid="stMetricValue"] {
        color: #15336b;
        font-weight: 800;
        font-size: clamp(1rem, 2vw, 1.8rem);
      }

      .stButton button,
      .stFormSubmitButton button {
        border-radius: 10px;
        font-weight: 750;
        min-height: 2.7rem;
      }

      .stButton button[kind="primary"],
      .stFormSubmitButton button[kind="primary"] {
        background: #1d4ed8;
        border: 1px solid #1d4ed8;
        color: #ffffff;
      }

      .stButton button[kind="primary"]:hover,
      .stFormSubmitButton button[kind="primary"]:hover {
        background: #173ea9;
        border-color: #173ea9;
        color: #ffffff;
      }

      [data-testid="stTextInput"] input,
      [data-testid="stTextArea"] textarea,
      [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #ffffff;
        border-color: #c9d7e9;
        border-radius: 9px;
      }

      [data-testid="stExpander"] {
        border: 1px solid #d8e3f1;
        border-radius: 12px;
        background: rgba(255,255,255,.96);
      }

      blockquote {
        border-left: 3px solid #2d63d6;
        border-radius: 0 8px 8px 0;
        background: #edf4ff;
        color: #172c50;
        padding: .6rem .9rem;
        margin: .3rem 0 .55rem;
      }

      hr {
        border-color: #dbe5f2;
      }

      footer {
        visibility: hidden;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------

LEGACY_DEFAULT_SCENARIO = (
    "Synthetic training scenario: A fictional supplier sends a message to a "
    "finance worker: 'The payment expires today. Act now and don't tell anyone "
    "or the contract will be lost.' The sender claims the finance director "
    "already approved the transfer, but the worker has not checked the request "
    "through the company's normal process."
)

if "scenario_text" not in st.session_state:
    st.session_state["scenario_text"] = ""
elif st.session_state["scenario_text"] == LEGACY_DEFAULT_SCENARIO:
    st.session_state["scenario_text"] = ""

if "qloo_entity_urns" not in st.session_state:
    st.session_state["qloo_entity_urns"] = ""

if "generation_notice" not in st.session_state:
    st.session_state["generation_notice"] = ""

if "qloo_search_result" not in st.session_state:
    st.session_state["qloo_search_result"] = None

if "qloo_search_message" not in st.session_state:
    st.session_state["qloo_search_message"] = ""

if "latest_report" not in st.session_state:
    st.session_state["latest_report"] = None

if "analysis_error" not in st.session_state:
    st.session_state["analysis_error"] = ""

settings = get_settings()


# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        '<div class="brand-lockup">◉ PANOPTICON</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Cognitive security · Cultural intelligence · Defensive analysis"
    )

    st.divider()
    st.markdown("**Provider configuration**")

    st.write(
        "Qloo API key:",
        "Detected" if settings.qloo_api_key else "Missing",
    )
    st.write(
        "Groq API key:",
        "Detected" if settings.groq_api_key else "Missing",
    )

    st.caption(
        "Detected means a key was loaded. It does not establish that "
        "the key is valid."
    )

    # Qloo live entity search
    st.divider()
    st.markdown("**Qloo cultural entity search**")

    st.caption(
        "Search for an entity by name. Search results come from Qloo. "
        "Choose a result to add its identifier to the analysis."
    )

    qloo_query = st.text_input(
        "Entity name",
        key="qloo_search_query",
        placeholder="e.g. Microsoft",
        max_chars=200,
    )

    entity_types = {
        "Any supported category": None,
        "Brand": "urn:entity:brand",
        "Artist": "urn:entity:artist",
        "Movie": "urn:entity:movie",
        "Book": "urn:entity:book",
        "Destination": "urn:entity:destination",
        "Person": "urn:entity:person",
        "Place": "urn:entity:place",
        "Podcast": "urn:entity:podcast",
        "TV show": "urn:entity:tv_show",
        "Video game": "urn:entity:videogame",
    }

    selected_type_label = st.selectbox(
        "Entity category",
        options=list(entity_types),
        key="qloo_search_type_label",
    )

    if st.button(
        "Search Qloo",
        key="search_qloo_button",
        use_container_width=True,
        disabled=not bool(settings.qloo_api_key),
    ):
        if not qloo_query.strip():
            st.session_state["qloo_search_message"] = (
                "Enter an entity name to search."
            )
            st.session_state["qloo_search_result"] = None
        else:
            try:
                with st.spinner("Searching Qloo..."):
                    result = QlooClient(settings).search_entities(
                        qloo_query,
                        entity_type=entity_types[selected_type_label],
                        take=10,
                    )

                st.session_state["qloo_search_result"] = result
                st.session_state["qloo_search_message"] = (
                    f"Qloo returned {result['result_count']} result(s)."
                )

            except QlooError as exc:
                st.session_state["qloo_search_result"] = None
                st.session_state["qloo_search_message"] = exc.public_message

            except Exception:
                logger.exception("Unexpected Qloo search error")
                st.session_state["qloo_search_result"] = None
                st.session_state["qloo_search_message"] = (
                    "Qloo search failed unexpectedly. "
                    "Check the VS Code terminal for details."
                )

    if not settings.qloo_api_key:
        st.caption("Add QLOO_API_KEY to .env to enable live search.")

    if st.session_state["qloo_search_message"]:
        if st.session_state.get("qloo_search_result"):
            st.success(st.session_state["qloo_search_message"])
        else:
            st.warning(st.session_state["qloo_search_message"])

    search_result = st.session_state.get("qloo_search_result")
    search_items = (
        search_result.get("items", [])
        if isinstance(search_result, dict)
        else []
    )

    if search_items:
        entity_options = list(range(len(search_items)))

        def entity_label(index: int) -> str:
            entity = search_items[index]
            name = entity.get("name", "Unnamed entity")
            identifier = entity.get("id", "ID unavailable")
            return f"{name} · {identifier}"

        selected_index = st.selectbox(
            "Search result",
            options=entity_options,
            format_func=entity_label,
            key="qloo_selected_result_index",
        )

        selected_entity = search_items[selected_index]

        with st.expander("Selected Qloo result details"):
            st.write("**Entity name**")
            st.write(selected_entity.get("name", "Not returned"))

            st.write("**Entity identifier**")
            st.code(
                str(selected_entity.get("id", "Not returned")),
                language="text",
            )

            st.write("**Entity category**")
            st.write(selected_entity.get("type", "Not returned by Qloo"))

        if st.button(
            "Add selected entity to analysis",
            key="add_qloo_entity_button",
            use_container_width=True,
        ):
            raw_identifier = selected_entity.get("id")

            try:
                if not isinstance(raw_identifier, str):
                    raise QlooError(
                        "Qloo did not return a usable entity identifier."
                    )

                # Accept either UUID identifiers or urn:entity:... IDs.
                validated_ids = parse_entity_ids([raw_identifier])

                if len(validated_ids) != 1:
                    raise QlooError(
                        "The selected Qloo result did not contain one valid ID."
                    )

                selected_identifier = validated_ids[0]

                existing_ids = parse_entity_ids(
                    st.session_state["qloo_entity_urns"]
                ) if st.session_state["qloo_entity_urns"].strip() else []

                if selected_identifier not in existing_ids:
                    existing_ids.append(selected_identifier)

                st.session_state["qloo_entity_urns"] = ", ".join(existing_ids)

                # Prevent old results from being mistaken for the new input.
                st.session_state["latest_report"] = None

                st.session_state["qloo_search_message"] = (
                    f"Added {selected_entity.get('name', selected_identifier)} "
                    "to the analysis input. Run the analysis again to query Qloo."
                )

            except QlooError as exc:
                st.session_state["qloo_search_message"] = exc.public_message

            st.rerun()

    # Optional Groq scenario generation
    with st.expander(
        "Optional: generate a synthetic training scenario",
        expanded=False,
    ):
        st.caption(
            "No scenario is generated automatically. Use this feature only "
            "when you want a fictional training example."
        )

        theme = st.text_input(
            "Training scenario theme",
            key="scenario_generation_theme",
            max_chars=300,
            placeholder="e.g. suspicious supplier payment request",
        )

        if st.button(
            "Generate training scenario with Groq",
            key="generate_scenario_button",
            use_container_width=True,
            disabled=not bool(settings.groq_api_key),
        ):
            if not theme.strip():
                st.session_state["generation_notice"] = (
                    "Enter a theme before generating a training scenario."
                )
            else:
                try:
                    with st.spinner("Generating a synthetic scenario..."):
                        generated = GroqClient(
                            settings
                        ).generate_synthetic_scenario(theme)

                    st.session_state["scenario_text"] = generated
                    st.session_state["generation_notice"] = (
                        "A synthetic training scenario was generated. "
                        "Review it before running analysis."
                    )

                except GroqError as exc:
                    st.session_state["generation_notice"] = exc.public_message

                except Exception:
                    logger.exception("Unexpected Groq generation error")
                    st.session_state["generation_notice"] = (
                        "Scenario generation failed unexpectedly. "
                        "Check the VS Code terminal."
                    )

            st.rerun()

    if st.session_state["generation_notice"]:
        st.info(st.session_state["generation_notice"])


# ---------------------------------------------------------------------
# MAIN PAGE
# ---------------------------------------------------------------------

st.markdown(
    '<div class="brand-lockup">DEFENSIVE INTELLIGENCE WORKBENCH</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero-title">PANOPTICON</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero-subtitle">'
    "Analyze a message for observable pressure tactics. Inspect the exact "
    "wording behind each finding, explore cultural entities returned by Qloo, "
    "and review practical defensive actions. A phrase match is a warning "
    "signal—not proof of intent."
    "</div>",
    unsafe_allow_html=True,
)

st.write("")

st.markdown(
    '<div class="section-eyebrow">01 / INPUT</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-heading">Message and context</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">'
    "Paste the message you want to examine. The input starts empty; "
    "no example or simulated result is preloaded."
    "</div>",
    unsafe_allow_html=True,
)

with st.form("analysis_form", clear_on_submit=False):
    scenario = st.text_area(
        "Message or scenario to analyze",
        key="scenario_text",
        height=245,
        max_chars=MAX_SCENARIO_CHARS,
        placeholder=(
            "Paste the message here. Include the request, deadline, "
            "and any stated consequences."
        ),
        help=(
            "Remove personal details that are not needed. "
            "Never enter API keys, passwords, or other secrets."
        ),
    )

    entity_urns = st.text_area(
        "Qloo entity IDs or URNs (optional)",
        key="qloo_entity_urns",
        height=80,
        placeholder=(
            "Search Qloo in the sidebar and add a result, or paste known "
            "UUID-style entity IDs or urn:entity:... identifiers."
        ),
        help=(
            "Qloo is queried only when identifiers are supplied and a key is "
            "configured. Cultural associations are not proof of individual traits."
        ),
    )

    submitted = st.form_submit_button(
        "Analyze message",
        type="primary",
        use_container_width=True,
    )


if submitted:
    st.session_state["latest_report"] = None
    st.session_state["analysis_error"] = ""

    try:
        with st.spinner("Validating input and running analysis..."):
            st.session_state["latest_report"] = PanopticonAgent(
                settings
            ).analyze(scenario, entity_urns)

    except ScenarioValidationError as exc:
        st.session_state["analysis_error"] = str(exc)

    except QlooError as exc:
        st.session_state["analysis_error"] = exc.public_message

    except Exception as exc:
        logger.exception("Unexpected PANOPTICON analysis error")
        st.session_state["analysis_error"] = (
            f"Analysis could not complete ({type(exc).__name__}). "
            "Check the VS Code terminal for technical details."
        )


if st.session_state["analysis_error"]:
    st.error(st.session_state["analysis_error"])


# ---------------------------------------------------------------------
# RESULTS
# ---------------------------------------------------------------------

report = st.session_state.get("latest_report")

if report:
    st.write("")

    st.markdown(
        '<div class="section-eyebrow">02 / RESULTS</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-heading">Analysis overview</div>',
        unsafe_allow_html=True,
    )

    risk_report = report.get("risk_report", {})
    findings = risk_report.get("findings", [])
    qloo = report.get("qloo_context", {})
    llm_summary = report.get("llm_summary")

    qloo_status = str(
        qloo.get("status", "unknown")
    ).replace("_", " ").title()

    llm_status = str(
        report.get("llm_status", "unknown")
    ).replace("_", " ").title()

    metrics = st.columns(4)

    metrics[0].metric("Signals identified", len(findings))
    metrics[1].metric(
        "Risk categories",
        risk_report.get("matched_categories", len(findings)),
    )
    metrics[2].metric("Qloo status", qloo_status)
    metrics[3].metric("Groq narrative", llm_status)

    if llm_summary:
        with st.container(border=True):
            st.markdown("**Analysis narrative**")
            st.write(
                llm_summary.get(
                    "summary",
                    "No narrative summary was returned.",
                )
            )
            st.caption(
                f"Generated by {llm_summary.get('provider', 'Groq')} · "
                f"model: {llm_summary.get('model', 'unspecified')}. "
                "Treat the narrative as secondary to quoted evidence."
            )

            with st.expander(
                "Cultural interpretation, limitations, and follow-up checks"
            ):
                st.write(
                    llm_summary.get(
                        "cultural_context",
                        "No cultural-context interpretation was returned.",
                    )
                )

                limitations = llm_summary.get("limitations", [])
                if limitations:
                    st.markdown("**Limitations**")
                    for limitation in limitations:
                        st.markdown(f"- {limitation}")

                next_steps = llm_summary.get("next_steps", [])
                if next_steps:
                    st.markdown("**Suggested follow-up checks**")
                    for next_step in next_steps:
                        st.markdown(f"- {next_step}")

    else:
        st.info(
            report.get(
                "llm_message",
                "No Groq narrative was returned. Deterministic findings remain available.",
            )
        )

    st.markdown("### Cognitive risk signals")

    if not findings:
        st.info(
            "No configured text patterns matched. "
            "This does not establish that the message is safe."
        )

    else:
        for index, finding in enumerate(findings, start=1):
            with st.container(border=True):
                left, right = st.columns([5, 1])

                with left:
                    st.markdown(
                        f"**{index:02d} · "
                        f"{finding.get('category', 'Uncategorized signal')}**"
                    )
                    st.write(
                        finding.get(
                            "explanation",
                            "No explanation was returned.",
                        )
                    )

                with right:
                    st.metric(
                        "Severity",
                        finding.get("severity", "Unrated"),
                    )

                st.markdown("**Exact evidence from the submitted text**")

                evidence = finding.get("evidence", [])

                if evidence:
                    for phrase in evidence:
                        st.markdown(f"> “{phrase}”")
                else:
                    st.caption("No exact phrase was recorded for this finding.")

                st.caption(
                    f"Match status: {finding.get('match_confidence', 'Not specified')}. "
                    f"{finding.get('confidence_note', '')}"
                )

                st.markdown("**Recommended defensive response**")
                st.write(
                    finding.get(
                        "defensive_response",
                        "Request independent review before acting.",
                    )
                )

    # Live Qloo results
    st.markdown("### Cultural intelligence · Qloo")

    if qloo.get("status") == "live_success":
        st.success(
            f"Live Qloo request completed. "
            f"{qloo.get('result_count', 0)} result row(s) returned."
        )

        items = qloo.get("items", [])
        display_rows: list[dict[str, Any]] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            row: dict[str, Any] = {}

            if item.get("tag") is not None:
                row["Tag returned by Qloo"] = item.get("tag")

            if item.get("name") is not None:
                row["Entity name returned by Qloo"] = item.get("name")

            if item.get("id") is not None:
                row["Entity ID returned by Qloo"] = item.get("id")

            if item.get("type") is not None:
                row["Entity category"] = item.get("type")

            if item.get("affinity") is not None:
                row["Affinity returned by Qloo"] = item.get("affinity")

            if row:
                display_rows.append(row)

        if display_rows:
            st.dataframe(
                display_rows,
                use_container_width=True,
                hide_index=True,
            )
        elif not items:
            st.info(
                "Qloo returned no result items. No cultural results were fabricated."
            )
        else:
            st.info(
                "Qloo returned rows without recognized display fields. "
                "Inspect the raw response."
            )

        st.caption(
            f"Source endpoint: {qloo.get('endpoint', settings.qloo_api_url)}"
        )

        with st.expander("Inspect raw response returned by Qloo"):
            st.json(qloo.get("raw_response"))

    elif qloo.get("status") == "not_requested":
        st.info(qloo.get("message", "No Qloo request was made."))

    elif qloo.get("status") == "not_configured":
        st.warning(qloo.get("message", "Qloo is not configured."))

    elif qloo.get("status") == "invalid_input":
        st.error(qloo.get("message", "The Qloo input was invalid."))

    else:
        st.error(
            qloo.get(
                "message",
                "The Qloo request did not complete successfully.",
            )
        )

    # Defensive actions
    st.markdown("### Defensive countermeasures")

    countermeasures = report.get("countermeasures", [])

    if countermeasures:
        for index, action in enumerate(countermeasures, start=1):
            with st.container(border=True):
                action_column, priority_column = st.columns([5, 1])

                with action_column:
                    st.markdown(
                        f"**{index:02d} · "
                        f"{action.get('action', 'Review the request independently.')}**"
                    )
                    st.caption(
                        action.get(
                            "reason",
                            "General defensive safeguard.",
                        )
                    )

                with priority_column:
                    st.markdown(
                        f"**{action.get('priority', 'Standard')}**"
                    )
    else:
        st.info(
            "No countermeasure items were returned. "
            "Review the submitted content before acting."
        )

    with st.expander("Workflow trace, assumptions, and limitations"):
        st.markdown("**Workflow status**")
        st.json(report.get("workflow_steps", []))

        st.markdown("**Rule-engine limitations**")
        st.write(
            risk_report.get(
                "assessment_note",
                "Rule-based triage only. A phrase match is not proof of intent.",
            )
        )

        st.write(
            "Cultural associations do not establish an individual's beliefs, "
            "intent, vulnerability, or behavior. Generated narratives may be "
            "incomplete and must not override exact message evidence or "
            "independent human review."
        )

        st.markdown("**Submitted text inspected**")
        st.code(report.get("scenario", ""), language="text")

        st.download_button(
            "Download analysis report (JSON)",
            data=json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            file_name="panopticon-analysis.json",
            mime="application/json",
            use_container_width=True,
        )

else:
    st.markdown(
        '<div class="section-eyebrow">02 / RESULTS</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-heading">Ready for analysis</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Paste a message above and choose Analyze message. "
        "Results will show detected wording, supporting evidence, "
        "Qloo request status, limitations, and defensive actions."
    )


st.divider()

st.caption(
    "PANOPTICON · Evidence-linked cognitive-security analysis · "
    "Cultural context is not causal proof · "
    "Human review remains required for high-stakes decisions"
)