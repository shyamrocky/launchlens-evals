# F2 v1 Experiment Note (Pre-Run)

**Current status:** Run complete and scored (November 17, 2026). F2 not adopted; dropped under the no-F2-v2 rule. See section 8.
**Original pre-run status:** Pre-run. Criteria set by the owner. Not yet run. No live calls made.
**Date written:** 2026-11-17
**Owner:** Shyam
**Prompt file:** `evals/prompts/f2_note_direction_v1.txt` (built in commit `852b192`; SHA-256 `e516756b5fe2b3d0b485ba506f1eb4a4aabc6332916327faa778012460f9a7d9`, matches the manifest). One LinkedIn-only paragraph, "LINKEDIN NOTE DIRECTION", appended after FORMAT TONE POLICY; unchanged.

All items below were confirmed or set by the owner on November 17, 2026, before the run. This note is committed to the repo before the owner gives the go.

## 1. Hypothesis

Telling the Writer that the PMM note's compatible audience, tone and emphasis should drive the LinkedIn post, and that the opening should vary instead of the default "Discover / Introducing a new twist on a classic" line, clears the tone failures on the 6 target cases without regressing the 3 controls or the other formats.

## 2. Targets and controls

The 6 targets are all 6 tone failures in the owner-confirmed baseline scores (the original baseline scores are official).

| Target | Baseline tone failure | Other baseline failures |
|---|---|---|
| N-01 | No young-adult voice | Descriptor (smooth); closing question in body |
| N-02 | No family framing | Descriptors (smooth, unique) |
| N-03 | No trade-buyer framing | Descriptors (smooth, innovative, #FlavorInnovation) |
| N-06 | Does not lead with flavor | Descriptors (innovation, smooth, unique, refreshing, distinct) |
| N-10 | Not witty, generic | Descriptors (bright, smooth) |
| KF-01 | No storytelling | Descriptor (smooth) |

**Controls:** N-12, N-14, E-04 (the same as F1). Each passes contract/citation, factual support and compliance at baseline.

**Total:** 6 targets + 3 controls = 9 calls.

All 6 targets also have descriptor failures. F2 is not expected to fix them (F1 was dropped), so a target can clear its tone failure and still fail factual support.

## 3. Success criteria

Set by the owner before the run, using the same structure as F1.

- **Target outcome:** the tone failure is cleared on at least 4 of 6 targets (6 to 2 or fewer, as predicted in report section 7.2).
- **Adoption rule:** F2 goes into the final combined prompt only if all of these hold:
  - at least 2 targets clear the tone failure;
  - no control regresses on any check (all 3 still pass contract/citation, factual support and compliance);
  - no newly critical case (a case that was not critical at baseline becoming critical); any new critical category on an already-critical case is reported;
  - **citation guard:** no net drop in email or blog citation passes against the baseline on the same 9 cases. Baseline on these 9 (confirmed by Codex from the saved outputs): email 7/9 (fails N-06, N-10), blog 9/9. Floors: email at least 7/9, blog at least 9/9. Each format must meet its own floor; every case-level regression is disclosed. The owner chose the strict floor (no slips allowed) to match F1, knowing that a single blog citation slip fails F2.
- **Reported, not part of the decision:**
  - Template opener, defined before the run:
    - **Primary (template family):** the opening line is "Discover / Introducing a new twist on a classic…" or a cosmetic variant such as "a fresh twist on a classic". Baseline: 7/9 (N-01, N-02, N-03, N-06, KF-01, N-12, E-04). Predicted: 2 or fewer.
    - **Secondary (literal):** only "Discover / Introducing a new twist on a classic…". Baseline: 5/9 (N-01, N-02, KF-01, N-12, E-04). Reported alongside.
  - Descriptor, formatting and M1 changes (baseline M1 on these 9: 8/9, N-01 fails; confirmed by Codex).
- This is F2's improvement target, not the final pass bar (compliance at least 22/24).

**Comparison:** adoption is judged against the baseline.

## 4. Out of scope

A good result must not be described as fixing:

- Descriptor failures (F1, dropped)
- Closing-question or hashtag repeats in the body (F3; M1 tracks them)
- Pre-existing baseline citation failures (email N-06, N-10). The guard only checks they do not get worse overall.
- Any request the rules decline (health, comparison, availability)

## 5. Run configuration (to be confirmed by Codex before the go)

- Run id: `f2_v1`
- Prompt and manifest: existing `evals/prompts/f2_note_direction_v1.txt` and `evals/experiments/f2_v1.json`, hashes pinned
- Cap: 9 calls; cost reservation $1.327104 (9 × $0.147456)
- Hermes temperature: 0; one attempt per case; no retries
- Tracing: mandatory, same metadata as F1
- Dry run with network and writes blocked before the go
- Sealed cases refused

## 6. Scoring

- Blind: 9 baseline and 9 F2 LinkedIn posts in a fresh shuffle with new labels (different from the P and Q labels); Codex holds the mapping.
- Same frozen scoring rules, applied unchanged.
- Code checks (M1, campaign brief, email, blog, ads) run on all 9 F2 outputs.
- Limit: the owner has seen the baseline posts, so blinding is partial.

## 7. Stop rule

- The runner stops before any call that would exceed the 9-call cap or the cost reservation.
- A failed call is recorded and not rerun.
- A control regression does not stop the run; F2 is then not adopted.
- **No F2 v2 (confirmed by the owner).** If F2 is not adopted, it is dropped and Phase 4 moves to F3.

## 8. Results

Run `f2_v1`, November 17, 2026. Pre-run note commit `15d44f0`. Scored blind by the owner (18 shuffled posts, R001–R018: 9 baseline, 9 F2); Codex joined the scores to the private mapping without editing any value. Scores file SHA-256 `252b040cf457ae82ce54534c311b214dcecd40861eef22f80ddc71d8c040b32a`.

| Item | Result | Notes |
|---|---|---|
| Targets cleared (tone) | 5 / 6 | Target 4 met. Cleared: N-01, N-02, N-06, N-10, KF-01. N-03 (trade framing) still fails |
| Controls held | 2 / 3 | N-14 and E-04 held. N-12 went from pass to critical (unsupported descriptor) |
| Newly critical cases | 1 (N-12) | No new critical category on already-critical cases |
| Email / blog citations (same 9) | 7 / 9, 8 / 9 | Email meets its floor (7). Blog misses its floor (9): N-02 new failure. Email: N-02 new, N-06 cleared, N-10 persistent |
| Template opener (of 9): family / literal | 4 / 3 | Baseline 7 / 5. Prediction of 2 or fewer family openers missed (reported only) |
| Other changes | Compliance 3 to 7; factual 3 to 2; M1 8 to 8 | M1 total hides turnover: N-01 cleared, N-02 gained a closing question in the body. N-02 cleared tone but still fails compliance on formatting |
| Cost and calls used | 9 / 9 calls, 0 errors, $0.143920; p50 34.53 s, p95 39.35 s | All traces delivered. Cost per passing draft $0.072 (baseline $0.047 on these 9) |
| Decision / next step | **Not adopted. F2 dropped (no F2 v2)** | Tone target met, but the control, newly-critical and blog-floor conditions failed. Next: F3 |

**Scorer consistency.** The blind re-score of the 9 baseline posts repeated the two differences seen in the F1 v2 packet (N-01 tone; N-10 compliance). The original scores stay official; tone clears are counted against the official six.

**Limits.** Several baseline posts were identical to ones scored in earlier packets, so blinding was weak. Results cover 9 working cases only; sealed cases untouched.

**What we learned.** The note-direction rule worked on what it targeted: tone failures fell from 6 to 1 and compliance rose from 3 to 7 of 9. It was rejected by its safeguards, not by its target: a control gained a descriptor, and one blog citation slipped under a zero-tolerance floor. N-12 is the control most sensitive to prompt changes, failing under F1 v1 and F2.
