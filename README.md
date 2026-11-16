# LaunchLens evaluations

This repository contains the inherited LaunchLens Week 3 baseline and
Week 4 evaluation work. Week 4 evaluates the Hermes Writer's LinkedIn
first draft while generating the full five-format package. It is a
component evaluation, not proof of end-to-end agent reliability.

Educational disclaimer: the Coca-Cola Cherry Float launch and associated
PMM/readiness scenarios are fictional and synthetic. This project is not
affiliated with or endorsed by The Coca-Cola Company.

LaunchLens is a launch-aware GTM content agent: one controller agent (Qwen3-30B) chooses research steps, a Writer (Hermes-4-405B) drafts five formats, and an independent Reviewer (Qwen3-30B) checks them. A code harness enforces the launch gate, required reviews, citations and budget; LaunchLens never publishes. The demo combines public product evidence with synthetic launch/readiness data.

## Architecture and execution

![LaunchLens architecture](docs/images/LaunchLens-architecture.jpg)
![LaunchLens execution flow](docs/images/LaunchLens-execution-flow.jpg)

## Three scenarios

- **US — Proceed:** draft a campaign brief, LinkedIn post, email, blog and three ad variations.
- **UK — Clarify:** pause for a human answer, then draft without availability wording.
- **India — Hold:** explain the launch restriction and block promotional drafting.

## Tech stack

Streamlit · LangGraph · Nebius · Pinecone · Notion · Google Drive · LangSmith

## Inherited Week 3 app setup

The instructions below describe the inherited application. Evaluation
runner commands will be documented after implementation and verification.
Use your own credentials; .env must never be committed.

Requires Python 3.12, uv, service access, and the demo's provisioned private evidence bindings and spending authorization. Credentials alone do not provision a runnable demo; see the [demo guide](docs/DEMO.md).

Copy `.env.example` to `.env` with permissions `0600`. Required variable names: `NEBIUS_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `NOTION_API_KEY`. Optional tracing: `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`.

Install:

```sh
uv sync --locked --no-python-downloads
uv sync --project tools/ui --locked --group offline-agent --no-python-downloads
```

Run from the repository root:

```sh
uv run --project tools/ui --locked --group offline-agent --no-python-downloads streamlit run streamlit_app.py
```

Open http://127.0.0.1:8520/.

[Demo walkthrough](docs/DEMO.md) · [Current status](docs/STATUS.md)

## Evaluation results

No Week 4 evaluation results have been published yet. Raw results and
outputs remain private in ignored evals/results/ and evals/outputs/.
Only owner-reviewed, curated results will be published.

## Credits and license

Development is assisted by OpenAI Codex (implementation) and Anthropic Claude (design, review and prompt drafting).
Product-source attribution is recorded in data/public_sources/product_source_manifest.csv.

No project license is currently granted. Third-party materials retain
their applicable rights and terms.
