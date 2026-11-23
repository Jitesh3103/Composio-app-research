# Composio App Research — Product Ops Case Study

## Status and honesty
This repository contains a working research-agent prototype, a 100-app input inventory, and a nine-app pilot assembled from official documentation. The remaining 91 records are deliberately marked `pending`. This is not a completed 100-app audit. No accuracy percentage or live deployment is claimed.

## Run
Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export OPENAI_API_KEY="..."
export TAVILY_API_KEY="..."
python src/research_agent.py --limit 100
```

Use `--limit 3` for a smoke test. The agent searches for vendor documentation, extracts structured fields, filters evidence URLs to results actually returned by search, and saves progress after each app. Missing evidence becomes `insufficient_evidence` or `needs_human_review`.

## Human verification
Copy `data/verification_template.csv` to `data/verification.csv`. Select a stratified sample across categories and auth patterns. Open official sources and label each field `correct` or `incorrect`, adding a reviewer note. Then run:

```bash
python src/verify_sample.py
```

The metric is field-level accuracy on the human-labeled sample only. Do not extrapolate it to all 100 apps.

## Composio SDK / MCP
`src/composio_mcp_smoke_test.py` demonstrates the current session-based MCP setup. It requires a real `COMPOSIO_API_KEY` and has not been run in this workspace. Current docs:
- https://docs.composio.dev/docs/quickstart
- https://docs.composio.dev/docs/sessions-via-mcp

The research crawler itself uses Tavily for public-doc discovery and OpenAI for structured extraction. Composio MCP provisioning is an optional extension, not falsely represented as an executed integration.

## Field definitions
- Auth methods: mechanisms explicitly documented by the vendor.
- Access model: credential self-service versus plan, admin or partner restrictions.
- API surface: public REST/GraphQL capability families, without guessed endpoint counts.
- MCP status: first-party, community, not found in reviewed evidence, or not checked.
- Buildability: product judgment based on auth, coverage, access friction and MCP readiness.
- Confidence: strength of available evidence, not model confidence alone.

## Deployment
`index.html` is static and can be hosted on GitHub Pages, Netlify or Vercel. No deployment or GitHub push has been performed from this workspace; no live URL is claimed.
