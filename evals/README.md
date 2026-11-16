# Writer component evaluation — Phase 0

Evaluate the unchanged Hermes Writer's LinkedIn first draft, before repair or
review. Every request still generates the five-format package; account for the
entire call. This does not establish end-to-end LaunchLens reliability.

Only `user_notes_data_only` changes in source content. Its authoritative input
hash and projection audit hashes must change accordingly. Evidence, PMM guidance,
launch permission, schema, CTA, three-hashtag rule, tone policy and prompt remain fixed.
Runtime validation rejects source drift, snapshot/hash mismatch and prompt drift.

## Scope and environment

Run from the repository root on `week4-evals`. Only the existing
`tools/agent_foundation` environment is needed. Production source, prompt/hash
checks, permissions, budgets, dependency declarations and lockfiles are unchanged.
The evaluation uses its own manifest, per-run authorization, call cap and records.

Run all evaluation tests, with Python 3.12:

```sh
PYTHONPATH=src:. tools/agent_foundation/.venv/bin/python -B -m unittest discover -s evals/tests -v
```

Tests use synthetic fixtures and mocked providers with sockets blocked. They do
not read saved runs, credentials, private notes or `.env`, or initialize tracing.
Their synthetic projection policy exists only inside test mocks. The runtime
uses the unchanged production projector and source-identity checks.

## Pinned input and baseline

`manifest.json` publishes a logical snapshot ID and its approved SHA-256, never a
private source path. Supply the owner-provisioned snapshot locally at runtime.
It must be the approved US/Proceed checkpoint with no drafts or previous Writer
attempts. The runner reads it but never edits it. A public checkout alone cannot
recreate this private input; synthetic tests run independently of it.

`prompts/baseline_v1.txt` is a byte-identical copy of production
`package_writer_v3.txt`. Both files and the production configuration/profile are
hash-checked. Future fixes must be separate prompt files and require separate
approval; this runner accepts only the unchanged baseline.

## Cases and dry run

The golden dataset is public by design. Do not ignore `evals/cases/`.
`evals/cases/golden_v0.json` contains the 30 owner-written notes converted verbatim
from the reviewed draft, plus approved claims, CTA, hashtag rule, scoring rules,
pass bars, provenance and the recorded sealed draw. It remains draft v0; v1 is
frozen only after review and the separately authorized smoke test.

Each record contains `case_id`, `type`, `slice`, `intent`, `pmm_note`,
`expected_behavior`, `critical_failures` and `sealed`. Types are `normal`, `edge`,
`known_failure`, `adversarial`; slices are `normal` or `pressure`. The reader
validates all 30 unique IDs and the 15/9/4/2 type counts. It maps `pmm_note` to
internal `user_notes` without editing text, retaining type/slice separately. Case
metadata and scoring rules never enter the Writer request.

The seed is fixed at **20261115**. Sealed IDs are **A-01, E-01, E-06, KF-03,
KF-04, N-05**. They are copied from the approved draw, never redrawn. Exactly
24 cases remain working. The reader's default working selection excludes all
sealed cases. Phase 0 refuses explicit sealed IDs, including direct execution;
this change does not enable sealed-set generation or scoring.

CLI mode defaults to `smoke`, requiring 5–6 explicit working IDs using
`--case-ids`. Their requested order is preserved. Unknown, duplicate and sealed
IDs are rejected. `--mode working` can select the working set for a dry run;
the existing per-run call cap still applies. Later-phase execution requires its
own approval and configuration. There is no silent first-six smoke selection.

Notes are limited
to 1,000 characters, matching the inherited input limit. No sealed cases enter
Phase 0. Before committing cases, apply the canonical provenance rules, pre-commit
scan and owner approval. The owner's typed-notes exception never permits copying
other saved-run fields, Reviewer findings or outputs into the dataset.

A dry run validates hashes and prepares requests without files, credentials,
traces or network activity. Use a local shell variable for the private snapshot:

```sh
PYTHONPATH=src:. tools/agent_foundation/.venv/bin/python -B -m evals.runner \
  --snapshot "$EVAL_SNAPSHOT" --cases evals/cases/golden_v0.json --run-label smoke_v0 \
  --mode smoke --case-ids "$CASE_1" "$CASE_2" "$CASE_3" "$CASE_4" "$CASE_5"
```

The case variables must be the owner's selected working IDs; no smoke selection
or execution is approved by this example. A dry run prepares at most the cap and
reports any cases beyond it. It never spends money. The mocked suite also covers
schema rejection, exact note mapping, sealed-case refusal and explicit selection.

## Separately authorized live execution

Do not execute live until the owner says **run smoke test**, provides the working
cases and pass bars, and resolves balance/spending approval. The manifest itself
is not spending authorization. No live execution is authorized by this build.

Live execution requires both `--live` and `--approval-file`, referring to a private
record under ignored `evals/outputs/`. After explicit owner authorization, that
record binds `owner_instruction` (the exact phrase `run smoke test`), `run_label`,
`manifest_hash`, `cases_hash`, `call_cap` and `reservation_usd`. Hashes are SHA-256
of the parsed JSON serialized with `launchlens.live_research.dumps`. Approval
records are never generated by dry runs or committed. This build creates none.

At separately authorized execution time, credentials must be securely provisioned
in the process environment. The runner uses the existing selected-key loader in
environment-only mode; it never opens `.env`, discovers unrelated service keys,
prints credentials or saves request headers. Do not paste secrets into command
arguments, tracked files or terminal output.

A hard maximum of six calls and $0.884736 reservation applies per run. A smaller
`--call-cap` is allowed only with matching authorization. Reserve $0.147456 before
each attempt; count transport failures and retain the reservation when usage is
unknown. Stop after unknown usage, with no automatic retry. Prices are configured
profile rates ($1/million input, $3/million output), not verified current pricing.
Provider timeout is 180 seconds; both output caps are 8,192 tokens. The timeout is
not typical latency. Historical median cost suggests about $0.08–$0.10 for 5–6
calls; the approved reservation is deliberately more conservative.

## Results and manual retries

Each unique run label exclusively reserves its own `evals/results/<label>.csv`
and `evals/outputs/<label>/`. Existing labels are refused. A row is flushed and
synced after each attempt; raw provider bytes are saved before parsing. Inputs,
approval, per-attempt reservations and final summary remain private. An
interruption may leave a claim without a completed row; reconcile it manually,
never automatically replay it or reuse its label. This is not a resumable runner.

Rows contain the requested run/case/attempt identity, timestamp, prompt file/hash,
snapshot hash, model, temperature, status, safe error category, input/output usage,
latency, estimated full-call cost, trace-ID field, extracted LinkedIn text and raw
output location. Unknown usage/cost is blank, never zero. The summary separates
known cost from retained unknown reservations. CSV posts are raw untrusted text;
import them as text when transferring to a spreadsheet.

Statuses: `returned`, `content_fail_unparseable`, `transport_error`, `timeout`.
An invalid envelope, incomplete generation, invalid JSON or unusable LinkedIn
structure is unparseable. Existing shape normalization is preserved; no prose or
citation repair is performed. Extract hook, body, CTA and hashtags without
rewriting. A returned post may still fail contract, citation, factual-support or
instruction scoring. Those checks and human scores are subsequent evaluation
work; `returned` is not a pass. Editorial quality remains advisory.

The trace-ID field is blank in Phase 0. LangSmith instrumentation/verification is
Phase 2 work under the plan's 30-minute time box; no tracing is enabled here.

A manual retry uses a **new** run label plus `--retry-of ORIGINAL_LABEL`, with its
own authorization. Only identical cases whose original attempt was a transport
error or timeout qualify. They become attempt 2; the original row is unchanged.
A third attempt or retry of a content failure is refused. Both attempts count in
cost/reliability reporting. Incomplete private artifacts require manual review.

Raw results, run IDs, trace IDs, private inputs and execution records never enter
Git. Only separately curated, scanned and owner-approved results may be published
under [the Week 4 guardrails](../docs/project-governance.md#week-4-public-repo-guardrails-and-build-in-public-rules).

Educational demo: fictional Coca-Cola Cherry Float launch and synthetic scenarios;
not affiliated with or endorsed by The Coca-Cola Company. Implementation is
AI-assisted by OpenAI Codex; design, review and prompt drafting also use Anthropic
Claude. Source attribution remains in the inherited public-source manifest.
