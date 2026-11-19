# Final Run Note (Pre-Run): final_v1 and drift_baseline_v1

**Current status:** Run complete, working and sealed rounds scored and joined (November 18, 2026). See section 9.
**Original pre-run status:** Pre-run. Criteria set by the owner. Not yet built or run. No live calls made.
**Date written:** 2026-11-18
**Owner:** Shyam

All items below were confirmed or set by the owner on November 18, 2026, before the final run. This note is committed to the repo before the owner gives the go. This is the one final round: no prompt changes after it.

## 1. What runs

| Run | Prompt | Cases | Calls |
|---|---|---|---|
| `final_v1` | Baseline plus F2: `evals/prompts/f2_note_direction_v1.txt`, SHA-256 `e516756b5fe2b3d0b485ba506f1eb4a4aabc6332916327faa778012460f9a7d9` | All 30: the 24 working cases and the 6 sealed cases (A-01, E-01, E-06, KF-03, KF-04, N-05) | 30 |
| `drift_baseline_v1` | Unchanged baseline: `evals/prompts/baseline_v1.txt`, SHA-256 `2198dd6d64f5adca13728b6460db14e0bd5e1ab55468534c3994df3ec890b505` | N-09, E-07, A-02 (chosen before any run) | 3 |
| **Total** | | | **33** |

Dataset `golden_v1.json` (SHA-256 `171b0af3…5ce21`), snapshot `us-proceed-pre-writer-v1` (SHA-256 `40b13add…99bff`), Hermes-4-405B, temperature 0, one attempt per case, no retries, tracing mandatory.

## 2. Why this prompt, and its label

No fix met its pre-registered adoption rule (F1 v1, F1 v2, F2, F3 v1, F3 v2; see their pre-run notes). Under the rule fixed before F3 ran, the final prompt is the baseline plus F2, **labelled exploratory: F2 did not meet its own adoption rule.** F2 was chosen because its target worked (tone failures cleared on 5 of 6). On its 9-case test it also made control N-12 critical and dropped one blog citation. The final run measures what F2 does across all 30 cases.

## 3. Pre-registered predictions

Written before the run, from the F2 experiment and the baseline:

- **Compliance** rises from the baseline's 13/24, because tone failures mostly clear, but stays **below the 22/24 bar**: F2 does not fix the formatting slips, so most of those remain.
- **Factual support** stays about where the baseline was (6/24), and **misses the 23/24 bar** with critical failures on normal cases. No adopted fix targets descriptors, and F2 added one in its test.
- **Contract and citation** stays at or near the baseline's 23/24, at or above the 95% bar.
- **Email and blog citations** may drop slightly against the baseline (F2's 9-case test lost one blog citation).
- **Cost per passing draft** stays above the $0.04 bar; **p95 latency** stays under 60 s.
- **Template-family opener** drops from the baseline's level.

## 4. How results are reported

- Against the **original pass bars**: contract and citation ≥95%; factual support ≥95% (≥23/24) with zero critical failures on normal cases; compliance ≥90% (≥22/24); p95 latency under 60 s; under $0.04 per passing draft.
- Baseline and final side by side, as raw counts and percentages, for: working 24, sealed 6, and all 30. **Working and sealed are reported separately.**
- By slice (normal and pressure) and by severity, as in the baseline.
- Every case-level regression and improvement, against the baseline.
- Code checks on all five formats (M1, campaign brief, email, blog, ads), with exact failure fields.
- Template-family opener counts, and emoji and exclamation counts under the same rule as F3 v2.
- Cost per passing draft and p50/p95 latency, both runs.
- There is no adoption decision in this run. The four-part rule is reported for information on the 24 working cases (controls N-12, N-14, E-04; citation floors against the baseline).

## 5. Drift check

- **Purpose:** check whether the model behind the API changed since the baseline run (November 16).
- **Method:** the three repeats use the unchanged baseline prompt. They are compared with their baseline outputs on: identical LinkedIn text (yes/no), owner scores (blind), and all code checks.
- **Pre-registered reading:**
  - If all three match the baseline on owner scores and code checks, there is **no evidence of drift**; final deltas are reported as prompt effects.
  - If any repeat differs on an owner score or code check, the drift is **reported next to the final results**, and the deltas are marked as possibly affected by drift. Text differences alone, with the same scores and checks, are noted but not counted as drift.

## 6. Scoring and the sealed reveal

1. **Working packet (blind):** 24 baseline posts, 24 final posts and 3 drift posts, shuffled with fresh labels (not P, Q, R, S or T). Codex holds the mapping. Claude scores; the owner checks judgment calls and **records the time scoring finishes**.
2. **Join:** Codex joins the working scores only after the owner sends them with the finish time.
3. **Sealed reveal:** only after the working scores are joined, Codex builds a second blind packet with the 6 sealed baseline posts and the 6 sealed final posts (12, shuffled, fresh labels). Scored the same way, with the finish time recorded. These posts have not been read by anyone before this step.
4. Same frozen scoring rules and owner decisions throughout, including: "fresh" meaning "new" is allowed; "a hint of" is an intensity descriptor; "delicious" is a quality claim. **Official baseline scores stay authoritative** for the 24 working cases; blind re-scores are reported separately.
5. The sealed baseline posts have no official score yet; their blind score in the reveal packet becomes their official score.

## 7. Run configuration (to be confirmed by Codex before the go)

- Run ids: `final_v1` (30) and `drift_baseline_v1` (3)
- Cap: 33 calls in total; cost reservation 33 × $0.147456 = $4.866048
- Sealed cases allowed only in `final_v1`, with their outputs stored unread until the reveal step
- Dry run with network and writes blocked before the go
- Trace delivery confirmed by a LangSmith query after the run

## 8. Stop rule

- The runner stops before any call that would exceed the cap or the reservation.
- A failed call is recorded and not rerun.
- **One final round only.** No prompt changes or reruns after seeing results. If the bars are missed, the remaining failures are reported in report section 8, "What is next."

## 9. Results

Build commit `e3ed38a`. Runs on November 18, drift first then final: 33/33 calls returned, 0 errors, no retries; $0.526900 total (drift $0.047468, final $0.479432). All 33 traces confirmed by a metadata-only LangSmith query, including the 6 sealed.

| Item | Baseline | Final (baseline + F2) | Notes |
|---|---|---|---|
| Contract and citation, working 24 (validator) | 23 / 24 | 24 / 24 | Bar ≥95%: met by both |
| Factual support, working 24 | 6 / 24 | 9 / 24 | Bar 23 / 24: missed |
| Compliance, working 24 | 13 / 24 | 17 / 24 | Bar 22 / 24: missed |
| Critical failures on normal cases | 10 / 14 | 8 / 14 | Bar 0: missed |
| Sealed 6: contract (validator) / factual / compliance | 5 / 2 / 5 | 5 / 3 / 5 | Passing drafts 1 to 3. KF-03 newly critical; E-01, KF-04 cleared |
| All 30: contract (validator) / factual / compliance | 28 / 8 / 18 | 29 / 12 / 22 | Bars: contract met by final only (baseline 93.3%); factual (29) and compliance (27) missed by both; critical normal 11 / 15 to 9 / 15 |
| Email / blog / ads citations, all 30 | 24 / 26 / 30 | 27 / 24 / 30 | Working 24: 19 / 22 / 24 to 21 / 19 / 24. First campaign-brief failure (E-02) |
| Cost per passing draft, all 30 | $0.118 | $0.053 | Bar under $0.04: missed (sealed 6 alone $0.032) |
| p50 / p95 latency, all 30 | 32.4 s / 38.8 s | 37.5 s / 47.7 s | Bar p95 under 60 s: met (one final call 65.4 s) |
| Drift repeats (N-09, E-07, A-02) | | All three texts differ | E-07 minor to critical; A-02 critical to pass; N-09 scores held, new email citation failure. **Possible drift flagged** under section 5 |
| Cost and calls used | | 33 / 33 calls, $0.526900 | |

**Predictions (section 3) against results.** Compliance rose but stayed under its bar; factual support missed its bar; contract held; cost per pass stayed above $0.04; p95 stayed under 60 s; the template opener fell (17 to 11 working). As predicted. Factual support rose by 3 on the working set, more than "near 6". Email rose (19 to 21 working) while blog fell (22 to 19), so the predicted drop held for blog only.

**Contract metric.** The owner's blind scores marked contract as pass for baseline KF-03 and final N-05, but the LinkedIn validator flags an invalid citation-field reference in both. Contract is reported from the validator, as the framework specifies; owner contract counts (29 / 30 to 30 / 30) are not presented as validator agreement.

**Blinding order.** Working round: scoring finished 19:30 PT; the mapping was last accessed at 15:32 PT (packet build) and next at 19:36 PT (join). Sealed round: scoring finished 19:58 PT; mapping created 19:52 PT, next accessed 20:00 PT (join). The sealed posts were read for the first time at the reveal.

**What we learned.** The final prompt improved tone and the opener, and lifted factual support and compliance by 4 cases each on all 30. It held every hard rule on the sealed set. It still misses the factual-support, compliance, zero-critical and cost bars, because unsupported descriptors remain the dominant failure. The drift check shows the same prompt at temperature 0 changes wording, and sometimes scores, from run to run, so single-sample deltas carry noise of about the same size as several of the effects measured. The recommended next step is a code check that detects unsupported descriptors and triggers a repair, measured with repeated samples per case.
