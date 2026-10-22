# PANOPTICON — Project State

Last updated: 2026-10-20

## Mission

Build an AI-assisted cognitive-security and cultural-intelligence app for synthetic scenario simulation, potential manipulation-pattern review, and defensive countermeasures. Do not infer individual psychological traits or treat cultural associations as causal proof.

## Repository inspection

- This environment did not contain the user's working repository.
- Only the uploaded project-instructions text file was available in `/mnt/data`.
- This directory is therefore a standalone starter scaffold, not a modification to the user's local repository.

## Architecture decisions

- Python + Streamlit for the minimum local demo UI.
- `PanopticonAgent` orchestrates Qloo retrieval, deterministic rule analysis, countermeasure mapping, and optional Groq reporting.
- Qloo client isolates external-service access and is only called when validated entity URNs and a configured key are present.
- Groq client is optional; the deterministic rule engine remains usable without an LLM key.
- Provider response errors are sanitized. No fabricated Qloo data is returned.
- Provider clients are isolated from the rule engine to enable mocked tests.
- Credentials use `.env`; `.env` is excluded by `.gitignore`.

## Checklist

- [~] Create initial standalone project scaffold.
- [~] Implement explainable phrase-rule engine and input validation.
- [~] Implement countermeasure mapping.
- [~] Implement Qloo `v2/insights` client based on public Qloo example.
- [~] Implement Groq scenario generation and constrained report layer.
- [~] Implement Streamlit workflow UI.
- [~] Write provider-mocked and deterministic unit tests.
- [ ] Execute tests in this environment after dependencies are installed.
- [ ] Launch Streamlit UI and verify local browser behavior.
- [ ] Verify live Qloo calls with the user's API key.
- [ ] Verify live Groq scenario generation and report with the user's API key.
- [ ] Integrate into the actual repository after repository files are made available.
- [ ] Confirm which hackathon and verify its final submission checklist.

Legend: `[ ]` not started; `[~]` code drafted but not yet runtime-verified; `[x]` implemented and verified; `[!]` blocked or failing.

## Known limitations and risks

- Exact Qloo response shape and current key permissions must be verified with a live call.
- This milestone accepts Qloo entity URNs; free-text entity resolution is not implemented.
- Phrase-rule findings are heuristic; the approach can miss context and produce false positives/negatives.
- Groq JSON may fail or return invalid data; deterministic findings remain available in that case.
- The application has not been deployed.

## Exact next step

Install `requirements.txt` in a virtual environment, run `python -m pytest -q`, fix any failures, then launch with `streamlit run app.py`. After the local smoke test, test live provider connections using credentials stored only in `.env`.
