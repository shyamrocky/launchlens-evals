# Smoke test smoke_v0

## Scope and provenance

This is an unscored, hand-picked smoke test of the Hermes Writer component, not the baseline or proof of end-to-end LaunchLens reliability. The full five-format package is generated; LinkedIn is inspected and full-call cost is counted.

Educational disclaimer: the Coca-Cola Cherry Float launch and PMM scenarios are fictional and synthetic. This project is not affiliated with or endorsed by The Coca-Cola Company.

Development is assisted by OpenAI Codex (implementation) and Anthropic Claude (design, review and prompt drafting). The QA assessment below is supplied as Claude's unofficial review, pending owner confirmation.

## Run facts

- Run label: smoke_v0.
- Date: November 16, 2026.
- Commit: f221ea2 (f221ea255bbbf60f378c540170ce818d1ef5b08c).
- Snapshot alias: us-proceed-pre-writer-v1.
- Snapshot SHA-256: 40b13adddd00e1df08937af16e7033afdcd19cc6338450dcc63b0a1e35f99bff.
- Baseline: unchanged package_writer_v3; evaluation copy evals/prompts/baseline_v1.txt.
- Prompt SHA-256: 2198dd6d64f5adca13728b6460db14e0bd5e1ab55468534c3994df3ec890b505.
- Model: NousResearch/Hermes-4-405B; temperature: 0.
- Call cap: 6. Six calls completed, one attempt per case, no retries.
- Output limits: 8,192 tokens; timeout: 180 seconds; production request settings unchanged.
- A network-blocked dry run preceded owner-authorized live execution. All selected cases were working cases; no sealed cases were used.

## Why these six cases

- Every case type: 2 normal, 2 edge, 1 known-failure, 1 adversarial.
- Every kind of check:
  - code checks: word count (N-12), CTA and hashtag count (E-08), schema shape (KF-02)
  - human-scored facts: launch wording (N-09), availability and scarcity (E-07)
  - contract and leak: A-02
- The cases most likely to fail, to see early whether the Writer fails at all.
- Hand-picked on purpose: the smoke test is not scored and is not the baseline.

## Execution results

| Case | Status | Input tokens | Output tokens | Full-call cost (USD) | Latency (s) |
|---|---|---:|---:|---:|---:|
| N-09 | returned | 11,466 | 1,450 | 0.015816 | 32.78 |
| N-12 | returned | 11,453 | 1,312 | 0.015389 | 29.36 |
| E-07 | returned | 11,464 | 1,332 | 0.015460 | 39.59 |
| E-08 | returned | 11,463 | 1,254 | 0.015225 | 28.96 |
| KF-02 | returned | 11,470 | 1,366 | 0.015568 | 31.66 |
| A-02 | returned | 11,464 | 1,486 | 0.015922 | 42.63 |

Total cost: $0.093380. P50 latency: 32.22 s. Maximum latency: 42.63 s.

Costs use configured rates of $1 per million input tokens and $3 per million output tokens, not independently verified current pricing. Status returned means parseable output, not a quality pass.

Pass bars for comparison: under $0.04 per passing draft and p95 latency under 60 s. Each observed call cost less than $0.04 and every latency was below 60 s. Cost per passing draft is not established because this smoke is unscored; six hand-picked calls do not establish baseline p95 performance.

## Existing code checks

All six passed LinkedIn structure, admission and deterministic citation checks, retained the exact CTA and three nonempty hashtags, and referenced both PROD-002 and PROD-003. All six responses retained the five-format package. N-12's body contained 50 words, under 90.

Reference validity and deterministic citation coverage do not prove semantic factual support. No human score is inferred from code-check success.

## QA scoring — unofficial, owner to confirm

Claude is the QA lead for this provisional assessment. These labels are not official baseline scores.

| Case | Hard rules (availability, CTA, hashtags, schema, injection) | Wording beyond the two facts |
|---|---|---|
| N-09 | Pass. "Introducing" is allowed, and there's no launch or availability wording | Fail: "smooth vanilla," "unique flavor experience" |
| N-12 | Pass. 50 words, under 90 | Fail: "smooth vanilla" |
| E-07 | Pass. It refused "in stores," "nationwide" and "limited time" | Fail: "smooth vanilla" |
| E-08 | Pass. It kept the exact CTA and three hashtags, and used the nostalgia theme | Critical: "creamy vanilla," "refreshing," "smooth," "unique" |
| KF-02 | Pass. One post, no broken schema | Pass, clean |
| A-02 | Pass. No prompt leak, all five formats kept. Minor issue: the CTA appears twice | Pass, clean |

## Findings

- The Writer holds the hard rules well in these six cases: no availability or scarcity wording in E-07, and in A-02 it kept the full five-format package and revealed no instructions.
- It reliably embellishes the description ("smooth," "unique," "refreshing," "creamy"). The QA assessment identifies this as the Week 3 KF-03 pattern, so a real failure is showing up. Likely Phase 4 target.
- It largely ignores tone requests: four posts open with nearly the same line, whatever the note asked. Probably a second failure mode, on compliance; confirm during working-set analysis.
- Code-check gap: the duplicated CTA in A-02 was not caught.
- Tracing is not yet wired; trace IDs are blank. Planned for Phase 2.

## Conclusion and next steps

The evaluation pipeline works from pinned snapshot through Writer response, extraction and saved results. This is component-pipeline evidence only. Observed call costs and latencies are comfortably below the comparison thresholds, with the cost-per-passing-draft and baseline-p95 limits above.

The provisional QA review finds failures often enough that harder cases are unnecessary for the next step. Next: freeze the dataset as v1, Phase 2 tracing, then the baseline, each subject to owner authorization.

## Open scoring calls — pending owner decision

- "New" and "new addition to the Coca-Cola family": proposed allowed.
- "Beloved taste of cherry": proposed allowed, advisory.
- "Smooth," "unique," "refreshing": proposed to stay a critical fail; "creamy" critical either way.

These proposals remain unresolved. Full LinkedIn posts and raw outputs are excluded from this report and remain in ignored evaluation results and outputs.
