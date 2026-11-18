# F1 v2 Experiment Note (Pre-Run)

**Status:** Pre-run. Criteria set by the owner. Prompt not built yet. No live calls made.
**Date written:** 2026-11-17
**Owner:** Shyam
**Follows:** F1 v1, not adopted (see `evals/reports/f1_v1_pre_run.md`, section 8)

All items below were confirmed or set by the owner on November 17, 2026, before the v2 prompt was built or run. This note is committed to the repo before the owner gives the go.

## 1. Why a v2

F1 v1 appended one LinkedIn-only paragraph to the end of the baseline prompt. It cleared the descriptor failure on 9 of 18 targets (target 14). Control N-12 regressed to a critical descriptor failure, and N-02 added a launch/availability phrase ("is here!"). Blog citation passes also dropped from 19 to 13 on the same 21 cases, a format the rule never mentioned.

## 2. Hypothesis

Three changes to how the same rule is delivered will clear more descriptor failures than v1 without regressing controls or other formats:

1. **Placement:** the descriptor rule sits with the LinkedIn output rules instead of at the end of the prompt.
2. **Self-check:** before returning, the Writer checks the LinkedIn hook, body and hashtags and removes any taste, texture, intensity or quality word that is not in the approved claim wording.
3. **Launch phrasing:** the rule names launch or availability phrasing such as "is here", "now available" and "arriving" as not allowed.

The approved facts, CTA, hashtag rule and all other prompt text stay unchanged. Exact wording is proposed by Codex after diagnosis and approved by the owner before the build.

## 3. Targets and controls (unchanged from v1)

Kept identical so v2 compares directly with v1 and the baseline.

- **Targets (18):** N-01, N-02, N-03, N-04, N-06, N-09, N-10, N-11, N-13, N-15, E-02, E-03, E-05, E-08, E-09, KF-01, KF-02, A-02. These are all 18 baseline descriptor failures; the recorded wording for each is in the v1 note, section 2.
- **Controls (3):** N-12, N-14, E-04. N-12 is the control v1 broke.
- **Total:** 21 calls.

## 4. Success criteria

All thresholds were set by the owner before the build. They are the same as v1, plus one added guard (the citation condition), so the results compare like for like.

- **Target outcome:** descriptor (factual-support) failure cleared on at least 14 of 18 targets.
- **Adoption rule:** F1 v2 goes into the final combined prompt only if all of these hold:
  - at least 2 targets clear the descriptor failure;
  - no control regresses on any check (all 3 still pass contract/citation, factual support and compliance);
  - no new critical failures on any target or control;
  - **new in v2:** no net drop in email or blog citation passes against the baseline on the same 21 cases (email at least 17/21, blog at least 19/21). This is a net check: a case-level citation regression can be offset by a fix elsewhere, but every case-level regression is still disclosed.
- Tone, formatting and M1 changes on targets are tracked and reported but are not part of the decision.
- This is F1's improvement target, not the final pass bar (factual support at least 23/24 with zero normal-case critical failures).

**Comparison:** adoption is judged against the baseline. v2 is also reported against v1, case by case.

## 5. Out of scope

Same as v1, section 4. A good result must not be described as fixing M1 repeats, tone, the N-08 contract failure or pre-existing baseline citation failures. The citation guard only checks that v2 does not make them worse overall.

## 6. Run configuration (to be confirmed by Codex before the go)

- Run id: `f1_v2`
- Prompt file: `evals/prompts/f1_claim_wording_v2.txt`, hash pinned in the manifest
- Cap: 21 calls; cost reservation as computed by the runner for 21 calls
- Hermes temperature: 0; one attempt per case; no retries
- Tracing: mandatory, same metadata as v1
- Dry run with network and writes blocked before the go
- Sealed cases refused

## 7. Scoring

- Blind, as in v1: 21 baseline and 21 v2 LinkedIn posts in a fresh shuffle with new anonymous labels; Codex holds the mapping.
- Same scoring rules, applied unchanged.
- Code checks (M1, campaign brief, email, blog, ads) run on all 21 v2 outputs.
- Limit: the owner has seen the baseline and v1 posts, so blinding is partial.

## 8. Stop rule

- The runner stops before any call that would exceed the 21-call cap or the cost reservation.
- A failed call is recorded and not rerun.
- A control regression does not stop the run; F1 v2 is then not adopted.
- **No v3 (confirmed by the owner).** If v2 is not adopted, F1 is dropped and Phase 4 moves to F2 and F3. Total prompt changes stay within the 3 to 4 allowed.

## 9. Results

*To be filled in after the run. Record misses and regressions as well as successes.*

| Item | Result | Notes |
|---|---|---|
| Targets cleared | ___ / 18 | v1: 9 / 18 |
| Controls held | ___ / 3 | v1: 2 / 3 |
| New critical failures | | v1: 1 (N-12) |
| Email / blog citations (same 21) | ___ / 21, ___ / 21 | baseline 17 / 19; v1 17 / 13 |
| Cost and calls used | | |
| Decision / next step | | |
