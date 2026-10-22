# PANOPTICON

**AI-assisted cognitive security, cultural intelligence, and synthetic scenario triage.**

Panopticon is a defensive training application. It inspects fictional messages for predefined pressure patterns, cites the exact phrases that matched, recommends protective steps, and can add cultural context from Qloo's API. An optional Groq LLM generates fictional scenarios and a constrained narrative summary.

## Current milestone

A first vertical slice is included:

- Streamlit interface for a fictional scenario.
- Explainable phrase-rule analysis for seven potential pressure patterns.
- Evidence excerpts tied directly to the scenario text.
- Defensive countermeasure mapping.
- Live Qloo `v2/insights` integration using entity URNs.
- Optional Groq scenario generation and analysis summary.
- Explicit states for missing credentials, HTTP failures, malformed responses, and absent provider data.
- Unit tests using mocked provider responses for isolated tests; no fake provider responses are shown by the UI.

## Important boundaries

- Rule matches are heuristic. They are not a validated psychological measurement, proof of intent, or proof of manipulation.
- No detected pattern does not mean a scenario is safe.
- Qloo outputs describe cultural associations; they do not establish a participant's beliefs, motives, or vulnerabilities.
- The first milestone does **not** resolve free-text cultural names into entity URNs. It uses the documented Qloo insights route with user-provided entity URNs and does not invent a search endpoint.
- Qloo and Groq live calls have not been tested with your credentials in this starter workspace. NOT VERIFIED: live API access, your API key permissions, live response compatibility, and deployed behavior.
- No actual hackathon has been conclusively identified from the project brief. The current Qloo Agentic Hackathon rules were reviewed as a reference, but confirm your specific event before claiming compliance.

## Requirements

- Python 3.11 or newer.
- A Qloo API key for live cultural-context retrieval.
- A Groq API key for LLM scenario generation and summaries. Without either key, the local rule engine still runs.

## Windows setup (PowerShell)

Open PowerShell in the folder containing `app.py` and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and add your own `QLOO_API_KEY` and/or `GROQ_API_KEY`. Do not add quotes unless they are part of the key. Never commit `.env`.

Start the interface:

```powershell
streamlit run app.py
```

Run automated tests:

```powershell
python -m pytest -q
```

## Provider integration notes

### Qloo

The client uses the public Qloo site example for `GET https://api.qloo.com/v2/insights`, `x-api-key`, `filter.type=urn:tag`, `signal.interests.entities`, and `take=6`. It preserves the actual `results` rows and only displays normalized `tag` / `affinity` fields when they are present. Other payload content is available in the raw-response expander. If access is denied or the response structure differs, the UI reports the limitation instead of generating replacement data.

Example entity URNs shown in Qloo's public example include:

```text
urn:entity:artist:brian-eno
urn:entity:brand:jil-sander
```

These are examples to test with your own API access—not a guarantee that every key has access to all entities.

### Groq

The app uses Groq's chat-completions API with the configurable `GROQ_MODEL` value. The default is `openai/gpt-oss-120b`, which is listed in Groq's current model documentation at the time this project scaffold was written. If this model is unavailable to your account, set `GROQ_MODEL` to a model you can access.

## File map

```text
panopticon/
├── app.py
├── .env.example
├── .gitignore
├── LICENSE
├── PROJECT_STATE.md
├── README.md
├── requirements.txt
├── panopticon/
│   ├── __init__.py
│   ├── config.py
│   ├── countermeasures.py
│   ├── groq_client.py
│   ├── qloo_client.py
│   ├── risk_engine.py
│   └── workflow.py
└── tests/
    ├── test_groq_client.py
    ├── test_qloo_client.py
    ├── test_risk_engine.py
    └── test_workflow.py
```

## Next milestone

Verify this starter inside the actual Panopticon repository, add/confirm API credentials locally, run the test suite, then perform one live Qloo request and one Groq request. Keep secrets out of logs and source control. Add entity-name resolution only after verifying the current endpoint and schema in the API documentation available to your Qloo account.

## Reference links

- Qloo homepage/API example: https://www.qloo.com/
- Qloo developer guide: https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide
- Groq GPT-OSS 120B model documentation: https://console.groq.com/docs/model/openai/gpt-oss-120b
- Current Qloo Agentic Hackathon official rules (confirm this is your event): https://qloo.devpost.com/rules
