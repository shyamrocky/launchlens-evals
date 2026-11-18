# F3 v2 Experiment Note (Pre-Run)

**Current status:** Run complete and scored (November 18, 2026). F3 v2 not adopted; F3 dropped (no v3). Final prompt falls back to baseline plus F2, labelled exploratory. See section 9.
**Original pre-run status:** Pre-run. Criteria set by the owner. Prompt not built yet. No live calls made.
**Date written:** 2026-11-18
**Owner:** Shyam
**Follows:** F3 v1, not adopted (see `evals/reports/f3_v1_pre_run.md`, section 9)
**Prompt file:** `evals/prompts/f3_field_placement_v2.txt`, SHA-256 `cea950e8c237eef2ba41c6c2e9cbb8050b0f45bc6c07fd8c8ae6e6e2f28a0826` (proposed by Codex; independently reproduced by Claude, along with v1's hash). It is the F3 v1 prompt byte for byte plus one appended sentence:

> When placing the LinkedIn text, preserve the existing package-wide field-coverage rule: any title, subject line, preview or headline in any format that states the flavor or inspiration must keep its own claim_references entry for that exact field. A citation on another field does not cover it.

All items below were confirmed or set by the owner on November 18, 2026, before the v2 prompt was built or run. This note is committed to the repo before the owner gives the go.

## 1. Why a v2

F3 v1 cleared all 6 formatting slips, but its safeguards failed. Blog citations fell from 9/9 to 5/9, all on blog titles; email gained a failure on a subject line; ads had its first failure, on a headline. Two controls (N-12, E-04) and one target (E-07) gained critical descriptors. The owner chose before F3 v1 ran to allow one second attempt.

## 2. Hypothesis

Keeping v1's placement rule and adding an explicit reminder that titles, subject lines and headlines need their own citation entries keeps the formatting fix while preventing the citation losses in the other formats.

1. **Placement rule (unchanged from v1):** closing question only in the CTA field, hashtags only in the hashtag field, never repeated in the hook or body.
2. **Field-coverage reminder (new):** when the LinkedIn text is placed, the rest of the package keeps the baseline's field-coverage rule; any title, subject line, preview or headline that states the flavor or the inspiration has its own citation entry.

Everything else in the prompt stays unchanged. Exact wording is proposed by Codex after diagnosis and approved by the owner before the build. v2 does not add a descriptor rule: two F1 attempts showed a prompt rule does not stop descriptors, so v2 is not expected to fix the new descriptor failures on N-12, E-04 and E-07.

## 3. Targets and controls (unchanged from v1)

Kept identical so v2 compares directly with v1 and the baseline.

- **Targets (6):** N-01, N-07, N-08, E-07, E-09, KF-02 (all 6 baseline formatting slips; details in the v1 note, section 2).
- **Controls (3):** N-12, N-14, E-04.
- **Total:** 9 calls.

## 4. Success criteria (unchanged from v1)

- **Target outcome:** the formatting slip cleared on all 6 of 6 targets, confirmed by both the owner's blind score and M1.
- **Adoption rule:** F3 v2 goes into the final prompt only if all of these hold:
  1. at least 2 targets clear the formatting slip;
  2. no control regresses on contract/citation, factual support or compliance;
  3. no newly critical case;
  4. **citation guard:** email at least 7/9 and blog at least 9/9 against the baseline on the same 9 cases, each format checked separately, with every case-level regression disclosed.
- **Reported, not part of the decision:** ads citation passes (baseline 9/9; v1 8/9), M1, descriptor and tone changes, emoji and exclamation use, latency. Emoji and exclamation marks are counted in the evaluation report with the same rule for baseline, v1 and v2: "!" counted literally, emoji counted as visible sequences, citation metadata excluded.

**Comparison:** adoption is judged against the baseline. v2 is also reported against v1, case by case.

## 5. Out of scope

Same as v1, section 4: descriptors, tone, the N-08 contract failure, and pre-existing email citation failures.

## 6. Run configuration (to be confirmed by Codex before the go)

- Run id: `f3_v2`
- Prompt and manifest: `evals/prompts/f3_field_placement_v2.txt` and `evals/experiments/f3_v2.json` (copy of f3_v1 with only run label, prompt file and hash changed); existing ancestry check accepts it; `f3_v2` registered in the runner
- Cap: 9 calls; cost reservation $1.327104 (9 × $0.147456)
- Hermes temperature: 0; one attempt per case; no retries
- Tracing: mandatory, same metadata as v1
- Dry run with network and writes blocked before the go
- Sealed cases refused

## 7. Scoring

- Blind: 9 baseline and 9 v2 LinkedIn posts in a fresh shuffle with new labels (not P, Q, R or S); Codex holds the mapping.
- Same frozen scoring rules and owner decisions, applied unchanged; official baseline scores stay authoritative.
- Controls are counted under the pre-registered definition (contract/citation, factual support, compliance); citation regressions on controls are reported under the citation guard.
- The owner records the time scoring finishes, to support the blinding order.
- Code checks (M1, campaign brief, email, blog, ads) run on all 9 v2 outputs.

## 8. Stop rule

- The runner stops before any call that would exceed the 9-call cap or the cost reservation.
- A failed call is recorded and not rerun.
- **No F3 v3.** If v2 is not adopted, F3 is dropped and the final prompt is the baseline plus F2, labelled exploratory (decided before F3 v1 ran).

## 9. Results

Run `f3_v2`, November 18, 2026. Build and pre-run note commit `4a639fb`. Scored blind by the owner (18 posts, T001–T018: 9 baseline, 9 v2); Codex joined the scores unchanged. All 9 traces confirmed in LangSmith by query.

| Item | Result | Notes |
|---|---|---|
| Targets cleared (formatting) | 6 / 6 | Same as v1. Owner score and M1 both clear |
| Controls held | 1 / 3 | Pre-registered definition: N-12 held (it had failed in v1). N-14 ("refreshing") and E-04 ("bright", "smooth", "distinct") became critical. N-12 gained an email citation failure, counted under the guard. v1: 1 / 3 |
| Newly critical cases | 4 | N-07 and N-08 (descriptors plus tone), N-14, E-04. v1: 3 |
| Email / blog citations (same 9) | 7 / 9, 8 / 9 | Email meets its floor (7). Blog misses its floor (9): KF-02, on the blog title. v1: 8 / 5. Email new failures E-09, N-12 (preview text); cleared E-07, KF-02 |
| Ads (reported) | 9 / 9 | Recovered from v1's 8 / 9 |
| M1 (of 9) | 9 / 9 | Baseline 3 / 9 |
| Emoji / exclamation (posts containing) | 0 / 2 | Baseline 6 / 6; v1 0 / 0 |
| Other changes | Contract 8 to 9; factual 6 to 3; compliance 3 to 7 | v1: factual 5, compliance 8. E-07 and KF-02 now pass everything |
| Cost and calls used | 9 / 9 calls, 0 errors, $0.143535; p50 41.82 s, p95 46.97 s | All 9 calls slower than baseline |
| Decision / next step | **Not adopted. F3 dropped (no v3)** | Target met, but the control, newly-critical and blog-floor conditions failed. Final prompt: baseline plus F2, labelled exploratory |

**Blinding order.** The owner recorded that scoring finished at 14:25 PT, in the planning record, before sending the scores. The mapping file was created at 13:30:24 PT when the packet was built; its next recorded access was 14:26:25 PT, during the join, which Codex started at 14:26:24 PT. This is the strongest blinding evidence of any experiment. Access time is still not a complete read log. (The finish time was left as a placeholder in the join prompt; the planning record holds it.)

**Scorer consistency.** The blind baseline re-score again differed on N-01 (tone) and N-08 (contract failure not visible in the post). Official scores stay authoritative.

**What we learned.** The field-coverage reminder did its job: blog failures fell from 4 to 1 and ads recovered. But the descriptor problem moved rather than shrank: different cases picked up taste words each time (N-12 in v1; N-07, N-08 and N-14 in v2), and factual support fell from 6 to 3 on these cases. Across all five experiments, any prompt change shifted the Writer's wording enough to add descriptors to some previously clean posts. A prompt rule alone cannot hold this; a code check that detects descriptors and triggers a repair is the stronger next step (report section 8).
