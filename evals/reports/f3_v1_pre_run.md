# F3 v1 Experiment Note (Pre-Run)

**Status:** Pre-run. Criteria set by the owner. Not yet run. No live calls made.
**Date written:** 2026-11-18
**Owner:** Shyam
**Prompt file:** `evals/prompts/f3_field_placement_v1.txt` (built in commit `852b192`; SHA-256 `bbdc02cd70d8c99d6ab5d49a160d26f60487b61d99464dc3a4e650d22e0332b6`, matches the manifest). One LinkedIn-only paragraph, "LINKEDIN FIELD PLACEMENT", appended after FORMAT TONE POLICY; unchanged.

All items below were confirmed or set by the owner on November 18, 2026, before the run. This note is committed to the repo before the owner gives the go.

## 1. Hypothesis

Telling the Writer to put the closing question only in the CTA field and the hashtags only in the hashtag field, never repeated in the hook or body, clears the formatting slips on the 6 target cases without regressing the 3 controls or the other formats.

## 2. Targets and controls

The 6 targets are all 6 formatting slips in the official baseline scores, each also flagged by the M1 code check.

| Target | Baseline formatting slip | Other baseline failures |
|---|---|---|
| N-01 | Closing question repeated in body | Descriptor (smooth); tone |
| N-07 | Closing question repeated in body | none (minor only) |
| N-08 | Hashtags repeated in body | Contract (invalid content field reference) |
| E-07 | Hashtags repeated in body | none (minor only) |
| E-09 | Closing question repeated in body | Descriptor (refreshing) |
| KF-02 | Hashtags repeated in body | Descriptors (refreshing, bold, smooth, unique, #SodaInnovation) |

**Controls:** N-12, N-14, E-04 (the same as F1 and F2).

**Total:** 6 targets + 3 controls = 9 calls.

Four targets have other failures that F3 is not expected to fix. N-07 and E-07 can pass everything if the slip clears, because their only baseline failure is formatting.

## 3. Success criteria

Set by the owner before the run, using the same four-part adoption rule as F1 v2 and F2.

- **Target outcome:** the formatting slip is cleared on all 6 of 6 targets, matching the prediction in report section 7.2 (6 to 0). A target counts as cleared when both the owner's blind score shows no formatting category and the M1 check passes.
- **Adoption rule:** F3 goes into the final combined prompt only if all of these hold:
  1. at least 2 targets clear the formatting slip;
  2. no control regresses on any check (all 3 still pass contract/citation, factual support and compliance);
  3. no newly critical case (a case that was not critical at baseline becoming critical);
  4. **citation guard:** no drop in email or blog citation passes against the baseline on the same 9 cases. Baseline on these 9 (confirmed by Codex from the saved outputs): email 7/9 (fails E-07, KF-02), blog 9/9. Floors: email at least 7/9, blog at least 9/9. Each format must meet its own floor; every case-level regression is disclosed.
- **Reported, not part of the decision:** M1 pass count (baseline on these 9: 3/9, confirmed by Codex; prediction 9/9), descriptor and tone changes, and the N-08 contract failure.
- This is F3's improvement target, not the final pass bar (compliance at least 22/24).

**Comparison:** adoption is judged against the baseline.

## 4. Out of scope

A good result must not be described as fixing:

- Descriptor failures (F1, dropped)
- Tone failures (F2, dropped)
- The N-08 contract failure (an invalid citation field reference, not a formatting slip). Clearing N-08's formatting slip does not mean its contract failure cleared.
- Pre-existing baseline email citation failures (E-07, KF-02)

## 5. Run configuration (to be confirmed by Codex before the go)

- Run id: `f3_v1`
- Prompt and manifest: existing `evals/prompts/f3_field_placement_v1.txt` and `evals/experiments/f3_v1.json`, hashes pinned
- Cap: 9 calls; cost reservation $1.327104 (9 × $0.147456)
- Hermes temperature: 0; one attempt per case; no retries
- Tracing: mandatory, same metadata as F1 and F2
- Dry run with network and writes blocked before the go
- Sealed cases refused

## 6. Scoring

- Blind: 9 baseline and 9 F3 LinkedIn posts in a fresh shuffle with new labels (not P, Q or R); Codex holds the mapping.
- Same frozen scoring rules, applied unchanged; official baseline scores stay authoritative.
- Code checks (M1, campaign brief, email, blog, ads) run on all 9 F3 outputs.
- Limit: the owner has seen the baseline posts in earlier packets, so blinding is partial.

## 7. Stop rule and second attempt

- The runner stops before any call that would exceed the 9-call cap or the cost reservation.
- A failed call is recorded and not rerun.
- A control regression does not stop the run; F3 v1 is then not adopted.
- **Second attempt (owner decision, made before this run):** if F3 v1 is not adopted, an F3 v2 may be pre-registered, with the same targets, controls, bar and four-part rule, before it is built or run. There is no F3 v3.
- Attempts are counted per fix: F1, F2 and F3 are 3 prompt changes, with F1 and F3 allowed two versions each.

## 8. Final prompt rule (owner decision, made before this run)

- If F3 v1 or F3 v2 is adopted, the final prompt is the baseline plus the adopted F3. Only adopted fixes go in.
- If neither F3 attempt is adopted, the final prompt is the baseline plus F2, labelled "exploratory: did not meet its own adoption rule".
- Either way, the final run covers all 30 cases plus the 3 drift repeats (N-09, E-07, A-02), then the joint sealed reveal.

## 9. Results

*To be filled in after the run. Record misses and regressions as well as successes.*

| Item | Result | Notes |
|---|---|---|
| Targets cleared (formatting) | ___ / 6 | |
| Controls held | ___ / 3 | |
| Newly critical cases | | |
| Email / blog citations (same 9) | ___ / 9, ___ / 9 | baseline 7 / 9 |
| M1 (of 9) | | baseline 3 / 9 |
| Cost and calls used | | |
| Decision / next step | | |
