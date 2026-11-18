# F1 v1 Experiment Note (Pre-Run)

**Current status:** Run complete and scored (November 17, 2026). F1 v1 not adopted; see section 8.
**Original pre-run status:** Pre-run. Dry run passed. Criteria set. Waiting for owner "go". No live calls made.
**Date written:** 2026-11-17
**Owner:** Shyam
**Repo commit:** `852b192923e1ff19217585d4aa84b457d7cff564` ("Add Phase 4 experiment path, prompts and M1 measurement"). Local and origin match, working tree clean. 36 tests and public-repo scans passed.

All items below were confirmed or set by the owner on November 17, 2026, before the run. This note is committed to the repo before the owner gives the go.

## 1. Hypothesis

The F1 v1 prompt changes reduce unsupported descriptor wording (factual-support failures, such as "smooth", "unique", "refreshing") in the 18 target outputs, without regressing the 3 control outputs.

## 2. Targets and controls

The 18 targets match all 18 descriptor failures in the owner-confirmed baseline scores. None are missing and none are extra. Every row was scored factual support: fail, severity: critical.

| Target | Unsupported wording recorded in baseline | Other recorded failures |
|---|---|---|
| N-01 | smooth | Tone, formatting |
| N-02 | smooth, unique | Tone |
| N-03 | smooth, innovative, #FlavorInnovation | Tone |
| N-04 | bright, smooth | none |
| N-06 | innovation, smooth, unique, refreshing, distinct | Tone |
| N-09 | smooth, unique | none |
| N-10 | bright, smooth | Tone |
| N-11 | refreshing, unique | none |
| N-13 | creamy, fruity, bright, unique, refreshing, smooth | none |
| N-15 | smooth | none |
| E-02 | smooth, unique | none |
| E-03 | refreshing | none |
| E-05 | smooth, unique | none |
| E-08 | refreshing, smooth, unique | none |
| E-09 | refreshing | Formatting |
| KF-01 | smooth | Tone |
| KF-02 | refreshing, bold, smooth, unique, #SodaInnovation | Formatting |
| A-02 | smooth | none |

**Controls:** N-12, N-14, E-04. Each has baseline passes on contract/citation, factual support and compliance.

**Total:** 18 targets + 3 controls = 21 calls.

## 3. Success criteria

All thresholds below were set by the owner before the run.

- Target outcome: the descriptor (factual-support) failure is cleared on at least 14 of 18 targets (about 78%; all 18 fail at baseline). This is the improvement target for F1 alone, not the final pass bar: the final combined prompt must still reach at least 23/24 factual support with zero normal-case critical failures.
- Adoption rule (agreed in the Phase 4 plan): F1 goes into the final combined prompt if at least 2 targets clear the descriptor failure and no control regresses on any check. Controls: all 3 must still pass contract/citation, factual support and compliance.
- No new critical failures on any target or control. Regressions on targets (contract, citation, compliance, formatting) are recorded and disclosed.
- Tone and formatting failures on targets are tracked but are not part of the pass/fail decision; any new ones are reported.

## 4. Out of scope

F1 v1 targets descriptor failures only. A good result must not be described as fixing any of the following, which remain separate checks:

- M1 body CTA repeats: N-01, N-07, E-09
- M1 body hashtags: N-08, E-07, KF-02
- Email citation coverage (19/24): failures N-06, N-10, E-02, E-07, KF-02
- Blog citation coverage (22/24): failures E-02, E-05
- Tone and formatting failures listed in the target table
- N-08 contract failure

## 5. Offline baseline (before F1)

- M1: 18/24 pass. No hook flags.
- Campaign brief and ads: 24/24 pass on all checks.
- Email citation coverage: 19/24.
- Blog citation coverage: 22/24.
- All other email and blog checks passed.
- Sealed outputs remained unopened.

## 6. Run configuration

- Run id: `f1_v1`
- Dry run passed: 18 targets plus controls N-12, N-14, E-04
- Cap: 21 calls
- Cost reservation: $3.096576
- All pinned hashes verified
- Hermes temperature: 0
- Tracing: mandatory
- Retries: none
- Dry run was done with network and writes blocked: zero live calls

## 7. Stop rule

Set by the owner before the run.

- The runner stops before any call that would exceed the 21-call cap or the $3.096576 reservation (a hard stop enforced in code, confirmed by Codex before the go).
- With no retries, a failed call is recorded as a failed call and not rerun in this experiment.
- If a control regresses, the run still finishes (regressions are only visible at scoring); F1 is then not adopted, and the regression is reported.

## 8. Results

Run `f1_v1`, November 17, 2026. Scored blind by the owner (42 shuffled posts: 21 baseline, 21 F1); Codex joined the scores to the private mapping without editing any value. Scores file SHA-256 `88956e9e290d711f51db97b5c0f207e4f697f31a66f6401f510e5cb09dda30d8`.

| Item | Result | Notes |
|---|---|---|
| Targets cleared | 9 / 18 (50%) | N-01, N-03, N-04, N-06, N-11, N-15, E-03, E-09, KF-02. Target was 14. Still failing: N-02, N-09, N-10, N-13, E-02, E-05, E-08, KF-01, A-02 ("unique" was the most common leftover word) |
| Controls held | 2 / 3 | N-14 and E-04 held. N-12 went from pass to critical fail ("refreshing flavor experience") |
| New critical failures | 1 case (N-12) | Also N-02 added an availability failure ("is here!"), but it was already critical at baseline |
| Other regressions | Compliance: N-04 (tone), N-13 (hashtag in hook) | Email citations: 4 new fails, 4 cleared (17 to 17). Blog citations: 8 new fails, 2 cleared (19 to 13). Campaign brief and ads: no change |
| Same-21 totals | Factual 3 to 11; compliance 13 to 13; contract 21 to 21; M1 18 to 20 | Aggregate gains do not override the failed control and new-critical rules |
| Cost and calls used | 21 / 21 calls, 0 errors, $0.332907; p50 33.79 s, p95 41.41 s | All traces delivered |
| Decision / next step | **Not adopted** under the pre-registered rule | Next step: owner decision between (A) F2 and F3 without F1, or (B) a pre-registered F1 v2 |

**Limits.** The owner had already seen the baseline posts, so blinding was partial. Results cover 21 working cases only; sealed cases untouched.

**What we learned.** A rule appended at the end of the prompt halved descriptor failures on the 18 targets (18 to 9) but did not stop them; counting the controls, descriptor failures went from 18 to 10 because N-12 regressed, and the model swapped one descriptor for another in a passing control. It also shifted citation behaviour in the blog, a format the rule did not mention. A prompt-only fix needs a wider safety net than its own targets.
