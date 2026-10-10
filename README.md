# Multi-agent DevOps Incident Analysis Suite

A runnable hackathon MVP for analyzing operational CSV logs using LangGraph, an OpenRouter-hosted chat model, lightweight retrieval-augmented generation (RAG), and optional Slack/Jira integrations.

## What it does

1. Upload a CSV containing operational logs.
2. Parse and normalize log records.
3. Retrieve relevant runbook/context snippets using a lightweight TF-IDF retriever.
4. Use specialist LLM nodes for log classification, diagnosis/remediation, and runbook/checklist synthesis.
5. Route critical incidents to ticket preparation and optional Slack/Jira integrations.
6. Display a structured report and let a human explicitly approve external actions.

**Safety defaults:** Slack/Jira are disabled unless configured. External actions require the UI approval checkbox. The app never executes remediation commands. Use synthetic or approved/redacted logs only.

## Requirements

- Python 3.10+
- An OpenRouter API key
- Optional: Slack Incoming Webhook URL
- Optional: Jira URL, email, API token, and project key

## Setup

### Windows Command Prompt

```bat
cd devops_incident_analysis_suite
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set `OPENROUTER_API_KEY`. Keep `.env` private; do not commit it.

### macOS/Linux

```bash
cd devops_incident_analysis_suite
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
python app.py
```

Open the local URL printed by Gradio.

## CSV format

Minimum recommended columns:

- `timestamp`
- `service`
- `level` (INFO/WARN/ERROR/CRITICAL)
- `message`

The parser also accepts common alternatives such as `time`, `component`, `severity`, `log_level`, `error`, `event`, and `details`. If your column names differ, map them in `src/log_parser.py`.

A sample file is in `data/sample_incident_logs.csv`.

## Runbook RAG

Place approved runbooks as `.txt` or `.md` files in `data/runbooks/`. The app splits the files into chunks and retrieves relevant chunks with TF-IDF lexical matching. This keeps the MVP inexpensive and easy to run locally. It is a baseline retriever, not a semantic vector database; for production, evaluate hybrid/embedding retrieval and access controls.

## OpenRouter configuration

Set:

```env
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Choose a model enabled in your OpenRouter account. Availability, pricing, context limits, and structured-output support vary by model. The app uses ordinary chat completions and parses JSON from model output rather than relying on provider-specific structured-output features.

## Optional Slack integration

Set `SLACK_WEBHOOK_URL` to a Slack Incoming Webhook URL. Slack actions remain unavailable if it is empty.

## Optional Jira integration

Set:
- `JIRA_BASE_URL`, e.g. `https://your-domain.atlassian.net`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY`

The app uses Jira Cloud REST API v3 basic authentication. Ensure the token has permission to create issues in the target project. Do not use a personal admin token for a demo.

## Tests

```bash
pytest -q
```

## Architecture

- `app.py`: Gradio UI and human approval gate
- `src/graph.py`: LangGraph workflow
- `src/agents.py`: LLM prompts and JSON parsing
- `src/log_parser.py`: CSV validation and normalization
- `src/rag.py`: local runbook retrieval
- `src/integrations.py`: Slack/Jira API clients
- `src/config.py`: environment configuration
- `src/schemas.py`: typed graph state and result models

## Important limitations

- Root-cause outputs are hypotheses, not proof.
- Confidence scores are model estimates and are not calibrated probabilities.
- Severity is model-assisted; review it against your organization's incident policy.
- CSV logs can contain secrets or prompt-injection text. Redact data and treat log contents as untrusted evidence.
- No production remediation is performed.
- Test all integrations in a sandbox before using real channels or Jira projects.
