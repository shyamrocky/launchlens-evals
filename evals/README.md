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
`evals/cases/golden_v1.json` contains the 30 owner-written notes converted verbatim
from the reviewed draft, plus approved claims, CTA, hashtag rule, scoring rules,
pass bars, provenance and the recorded sealed draw. Version v1 is frozen after
owner review and smoke testing; golden_v0.json remains unchanged as history.
The frozen rules allow "new" and the brand name, treat "beloved" for cherry as
allowed/advisory, and mark unsupported product descriptors as critical failures.
The manifest pins the dataset file and its exact byte hash. The CLI defaults to
that file; an explicit --cases file must match the pinned hash. Hash drift is
rejected before snapshot preparation. The reader requires version v1/status frozen.

Each record contains `case_id`, `type`, `slice`, `intent`, `pmm_note`,
`expected_behavior`, `critical_failures` and `sealed`. Types are `normal`, `edge`,
`known_failure`, `adversarial`; slices are `normal` or `pressure`. The reader
validates all 30 unique IDs and the 15/9/4/2 type counts. It maps `pmm_note` to
internal `user_notes` without editing text, retaining type/slice separately. Case
metadata and scoring rules never enter the Writer request.

The seed is fixed at **20261115**. Sealed IDs are **A-01, E-01, E-06, KF-03,
KF-04, N-05**. They are copied from the approved draw, never redrawn. Exactly
24 cases remain working. The reader's default working selection excludes all
sealed cases. Smoke and ordinary working modes refuse sealed IDs, including
direct execution. Only the separately authorized baseline mode may generate them;
it does not enable sealed-set scoring or content inspection.

CLI mode defaults to `smoke`, requiring 5–6 explicit working IDs using
`--case-ids`. Their requested order is preserved. Unknown, duplicate and sealed
IDs are rejected. `--mode working` can select the working set for a dry run;
the existing per-run call cap still applies. Later-phase execution requires its
own approval and configuration. There is no silent first-six smoke selection.

Notes are limited
to 1,000 characters, matching the inherited input limit. No sealed cases enter
smoke mode. Before committing cases, apply the canonical provenance rules, pre-commit
scan and owner approval. The owner's typed-notes exception never permits copying
other saved-run fields, Reviewer findings or outputs into the dataset.

A dry run validates hashes and prepares requests without files, credentials,
traces or network activity. Use a local shell variable for the private snapshot:

```sh
PYTHONPATH=src:. tools/agent_foundation/.venv/bin/python -B -m evals.runner \
  --snapshot "$EVAL_SNAPSHOT" --run-label dry_v1 \
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

Outside the baseline-only exception below, a hard maximum of six calls and
$0.884736 reservation applies per run. A smaller
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

## Optional evaluation tracing

Tracing is evaluation-only and explicitly enabled with --trace on a live run.
Dry runs never initialize it. The runner reads only process-environment values:
LANGSMITH_API_KEY, LANGSMITH_PROJECT and the existing NEBIUS_API_KEY. An explicitly
owner-approved local wrapper may load only these selected settings into memory;
the runner never reads .env. The project must be launchlens-evals. Credentials
must never be printed, logged, saved, traced or included in command arguments.

Each case gets one locally assigned trace UUID and one Writer LLM child. The
exporter queues one completed batch per case with no retry. SDK enrichment,
implicit batching and transport retries are off. Exported inputs contain only
the public case note; outputs contain the extracted LinkedIn post and usage.
The full prepared request, prompt text, snapshot, evidence/source identifiers,
headers, raw response, private paths and exception messages are never exported.
Both selected secrets are redacted from allowed values before dispatch. Metadata
includes run/case identity, dataset version/hash, prompt file/hash, model,
temperature, attempt status, tokens, configured-price cost, latency and safe error.
The child represents the actual single HTTP attempt; its timestamps exclude
telemetry delivery. This is deliberately partial input capture, not the full wire.

Attempt rows are flushed before telemetry submission. New rows include
trace_status (disabled, pending, or trace failed) and the local trace UUID.
A UUID or pending status does not prove delivery. Late outcomes are appended to
ignored evals/outputs/<label>/trace-status.jsonl as delivered or trace failed.
evals.tracing.resolved_rows(results_path, sidecar_path) joins those events for
reports without rewriting CSV rows. Partial/truncated events do not claim success.
Queue overflow, client failures and configuration errors cannot fail or retry the
Writer. Missing sidecar events remain pending, never silently marked delivered.

The run_evaluation API never waits for HTTP by default. The CLI with --trace
allows up to 10 seconds of observation after all Writer attempts and durable
rows are complete; this does not enter Writer latency or delay a subsequent
Writer call. A short-lived process may lose queued telemetry at exit. Use an
owner-approved post-run observer for the live verification; failed/pending
telemetry is not grounds for another Writer call. No paid call, trace upload or
baseline cap increase is authorized merely by enabling this flag.

The owner lifted the original 30-minute tracing limit for this implementation.
Production tracing and all generation settings remain unchanged.

A manual retry uses a **new** run label plus `--retry-of ORIGINAL_LABEL`, with its
own authorization. Only identical cases whose original attempt was a transport
error or timeout qualify. They become attempt 2; the original row is unchanged.
A third attempt or retry of a content failure is refused. Both attempts count in
cost/reliability reporting. Incomplete private artifacts require manual review.

## Baseline-only mode and sealed-output isolation

The baseline exception is valid only for --mode baseline --run-label baseline_v1.
It requires all 30 exact cases from the hash-pinned frozen v1 dataset, in dataset
order. Partial selections, case overrides, retries, other labels and caps other
than 30 are refused. The manifest retains its ordinary six-call/$0.884736 policy
and adds a separate baseline policy: 30 calls, reservation $4.423680 (30 times
$0.147456). Model, temperature 0, production prompt/hash, request settings,
permissions and transport remain unchanged. Neither mode nor manifest grants
permission to spend; a separate owner go is required after the dry-run checkpoint.

A baseline authorization binds owner_instruction=run baseline, mode=baseline,
run_label, manifest_hash, cases_hash, dataset_hash, sorted sealed_ids, call_cap=30
and reservation_usd=4.423680. Smoke authorizations do not authorize the baseline.
Baseline manual retries are refused until separately approved and implemented.
Each case has one attempt. Errors are recorded without replay. Only in baseline
mode, unknown usage retains the full per-attempt reservation and execution
continues within the 30-call bound; ordinary modes still stop on unknown usage.
Local response-persistence failures stop execution. No run artifacts are overwritten.

Baseline output paths, all ignored and private:

- evals/results/baseline_v1.csv: working 24 only, including extracted post text.
- evals/results/baseline_v1_sealed.csv: sealed six content, never opened for reports.
- evals/results/baseline_v1_sealed_metrics.csv: allowlisted metrics only.
- evals/outputs/baseline_v1/working/: working raw responses and attempt claims.
- evals/outputs/baseline_v1/sealed/: sealed raw responses and attempt claims.

Both content CSVs and the sealed metrics CSV are exclusively created, with each
attempt flushed/fsynced immediately. Sealed parsing/extraction only stores output
and determines attempt status; no contract, citation or other content checks run
on it. Neither console summaries nor reports expose sealed post text, raw output,
code-check details or error messages. Sealed IDs/notes are not added to reports.

Baseline tracing is enabled automatically. It retains one root and one Writer
child per case, with asynchronous best-effort delivery. Sealed traces have empty
inputs and only status/usage outputs; no case note or post text is exported.
Metadata still identifies the experiment/settings and numeric attempt metrics.
Working traces retain their existing allowlisted content. Confirm delivery only
from the append-only local sidecar; never use deprecated run-read APIs.

Offline reporting uses evals/reporting.py. It opens the working CSV/responses and
the sealed metrics CSV, never the sealed content CSV or sealed raw responses.
The generic trace-status join also rejects sealed content CSVs. Code checks run
only on working returned responses; factual support remains human review. Sealed
reporting produces numeric/status aggregates only. Totals include every recorded
attempt, unknown-cost reservations and all-attempt latency. P95 uses inclusive
linear interpolation. No report, result or raw artifact is a public commit candidate.

Network-blocked dry-run shape (no spending authorization is created):

```sh
PYTHONPATH=src:. tools/agent_foundation/.venv/bin/python -B -m evals.runner \
  --snapshot "$EVAL_SNAPSHOT" --mode baseline --run-label baseline_v1 --trace
```

After a separately approved live run, offline working/sealed-safe reporting:

```sh
PYTHONPATH=src:. tools/agent_foundation/.venv/bin/python -B -m evals.reporting \
  --snapshot "$EVAL_SNAPSHOT"
```

Raw results, run IDs, trace IDs, private inputs and execution records never enter
Git. Only separately curated, scanned and owner-approved results may be published
under [the Week 4 guardrails](../docs/project-governance.md#week-4-public-repo-guardrails-and-build-in-public-rules).

Educational demo: fictional Coca-Cola Cherry Float launch and synthetic scenarios;
not affiliated with or endorsed by The Coca-Cola Company. Implementation is
AI-assisted by OpenAI Codex; design, review and prompt drafting also use Anthropic
Claude. Source attribution remains in the inherited public-source manifest.

## Phase 4 isolated experiments — staged owner review

The current implementation registers only f1_v1, f2_v1 and f3_v1. Each prompt is
an independently hash-pinned addition to the unchanged baseline; no fixes are
combined yet. Production ContentCall and its prompt/hash/permission checks are
unchanged. The experiment builder uses the existing input/projector/schema and
asserts that, for the same case, only the system message differs from production.
It then validates its own manifest-bound request before the unchanged ProviderHTTP
transport. No production function or private attribute is monkeypatched.

| Run | Fix | Targets | Controls | Cap | Reservation USD |
|---|---|---:|---:|---:|---:|
| f1_v1 | F1: approved claim wording | 18 | 3 | 21 | 3.096576 |
| f2_v1 | F2: note tone/audience | 6 | 3 | 9 | 1.327104 |
| f3_v1 | F3: field placement | 6 | 3 | 9 | 1.327104 |

Controls are N-12, N-14 and E-04. Ordered IDs live in each public experiment
manifest and must match the approved registry. Sealed IDs, altered settings,
modified prompt/dataset/parent hashes, unregistered labels and reused outputs are
refused. Manifest bounds are maximums, not permission to spend. Each live run
needs its own owner go and private authorization binding owner_instruction=run
experiment, mode=experiment, run_label, manifest_hash, cases_hash, dataset_hash,
candidate_prompt_hash, call_cap, reservation_usd and tracing_required=true.
Manifest/case authorization hashes use parsed JSON serialized with the existing
dumps helper. Parent/prompt/dataset hashes bind exact file bytes.

No automatic retry or resume. Every attempted call gets one durable CSV row and
its raw response (when received), including failed/unparseable attempts. Unknown
usage retains $0.147456 and stops the experiment, preserving the existing ordinary
run rule. Output, claim, approval, source and measurement records stay in ignored
results/outputs. Existing baseline artifacts are never overwritten.

Tracing is mandatory: no disable option exists for Phase 4. Environment-only live
provisioning requires the selected LangSmith key and project; HTTP delivery remains
best effort and never retries or blocks Writer execution. Every case has one root
and one Writer child. In addition to existing metadata, both carry fix_id,
candidate_prompt_file/hash, run_label, case_role (target/control) and allowlisted
M1 flags. Working traces contain only the note and extracted post plus usage.
Sealed trace metadata supports baseline/final identities but always defers M1 and
excludes note/post content. Final/drift generation is not enabled by these three
manifests; its frozen prompt and separate manifests require later review.

M1 version m1-v2-hook-body checks BOTH linkedin.content.hook and .body for the
literal supplied CTA and any hashtag token (# followed by Unicode word characters).
It reports per-field exact_cta/hashtag booleans and formatting_pass. Paraphrased
questions remain human judgment. A measured failure is a minor compliance issue;
M1 never rewrites attempt status, contract/citation scores, text or references.
Unavailable content is not_evaluated; sealed content is deferred_sealed and is
never inspected. Each experiment records the same M1 flags in its row, private
measurement record and trace. Existing validators independently check all five
formats; those findings do not substitute for human factual/compliance scoring.

The explicit Stage b measure_saved_baseline helper applies M1 and the existing
four-other-format checks to saved WORKING baseline responses only. It writes a
new ignored versioned measurement document, preserving original attempts. It is
not invoked on import, by tests on real data, or by dry runs. Stage a does not
apply it. Sealed baseline responses remain unopened and unchecked until the joint
baseline/final reveal.

Owner-score import preserves the source CSV byte-for-byte and stores an ignored
JSON copy with identical column order, row order and string values. It validates
exactly 24 unique working IDs and accepted labels; it never repairs labels,
infers scores or changes notes. Real owner data is not a test fixture and is never
copied into maintained files. The importer refuses overwrites and records the
source hash; it makes no service calls. CSV text must be imported as text when
used in spreadsheet software.

### Proposed feedback attachment after unblinding — no upload yet

After the owner locks/unblinds scores, prepare feedback using local case-ID to
root-trace-ID joins and delivered sidecar events, including existing baseline
working traces. Do not read runs back from LangSmith. For each case-root trace:

| Feedback key | Owner source | Feedback representation |
|---|---|---|
| contract | contract_citation | score 1/0 for pass/fail; value preserves source label |
| factual_support | factual_support | score 1/0; value preserves source label |
| compliance | compliance | score 1/0; value preserves source label |
| failure_category | failure_category | original string value, including multiple categories |
| severity | severity | original string value |

The offline feedback_plan helper currently supports the imported baseline working
scores only and refuses planning before unblinded=true, undelivered traces,
changed source values or sealed rows. It creates no client and never uploads.
A later separately authorized publisher can call Client.create_feedback with
run_id/trace_id from the local root, key, score/value, deterministic feedback_id
and stop_after_attempt=1 (the installed SDK default would otherwise retry).
Keep a private append-only acknowledgment outbox, omit post text/owner notes and
credentials, and do not silently replay failed/unknown writes. Numeric feedback
is a derived encoding; the imported owner values remain unchanged. No deprecated
read-back calls are needed. Final/experiment score imports and publishing require
their own reviewed release. Sealed feedback is forbidden before the joint reveal.

### Final round and version-masked scoring

Only one final round is planned. Combine fixes only after measured owner review,
freeze the combined prompt, then separately authorize final_v1 on all 30 and
unchanged-baseline repeats N-09/E-07/A-02, reported separately. If the combined
prompt misses pass bars, report remaining failures; no further iteration without
a new owner decision. This implementation cannot execute unregistered final runs.

For blind scoring, shuffle anonymous output labels and keep the mapping/seed in
a separate ignored private file. Hide run/prompt identity, costs, latency and trace
links until scoring is locked. Keep working and sealed packets separate; reveal
sealed baseline/final together only after final prompt freeze and final generation.
Record prior baseline exposure as a limitation. No sheet or reveal is generated
by the current build. Regressions must be checked across all quality metrics for
both targets and controls; require at least two improvements and no control
regression. Final acceptance uses the frozen full-set bars, not subset targets.

The owner reports a private external backup is already complete. The build does
not access that location or make another archive. Commit approval is the next
stop; Stage b baseline measurements and Stage c actual f1_v1 dry run follow only
after their requested approval boundaries. No paid run or feedback upload is
implicitly authorized by these instructions or example commands.
