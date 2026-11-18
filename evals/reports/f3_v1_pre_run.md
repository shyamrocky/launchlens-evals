# F3 v1 Experiment Note (Pre-Run)

**Current status:** Run complete, scored and independently audited (November 18, 2026). F3 v1 not adopted; an F3 v2 is allowed under section 7. See section 9.
**Original pre-run status:** Pre-run. Criteria set by the owner. Not yet run. No live calls made.
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

Run `f3_v1`, November 18, 2026. Pre-run note commit `a04fbcd` at 17:10:27Z, 261 seconds before the first call (17:14:48Z); committed note SHA-256 `dfdf77d3…ad10a5`. Scored blind by the owner (18 shuffled posts, S001–S018: 9 baseline, 9 F3); Codex joined the scores without editing any value. Scores file SHA-256 `f306dab90cfa75ae38d95dfef3f44d8dbbc3e806281bf446789eb7375e49dd82`.

| Item | Result | Notes |
|---|---|---|
| Targets cleared (formatting) | 6 / 6 | Target met. Confirmed by both owner scores and M1 |
| Controls held | 1 / 3 | Pre-registered definition (contract/citation, factual support, compliance): N-14 held; N-12 and E-04 gained critical descriptors. N-14 also gained a blog citation failure, counted under the citation guard |
| Newly critical cases | 3 | E-07 ("smooth", "creamy appeal"), N-12 ("bright", "smooth", "unique"), E-04 ("smooth") |
| Email / blog citations (same 9) | 8 / 9, 5 / 9 | Email passes its floor (7). Blog fails its floor (9): new failures E-04, E-07, KF-02, N-14, all on the blog title. Email: N-08 new (subject line); E-07, KF-02 cleared |
| Ads (reported) | 8 / 9 | First ads failure in any run: E-04, citation coverage on an ad headline |
| M1 (of 9) | 9 / 9 | Baseline 3 / 9 |
| Other changes | Contract 8 to 9; factual 6 to 5; compliance 3 to 8; overall passes 3 to 5 | E-09 and KF-02 now pass everything; N-08's contract failure also cleared in this sample |
| Cost and calls used | 9 / 9 calls, 0 errors, $0.142239; p50 41.79 s, p95 50.54 s | All 9 calls slower than baseline (baseline p95 35.79 s on these 9). Cost per passing draft $0.028 (baseline $0.047) |
| Decision / next step | **Not adopted** | Target met, but the control, newly-critical and blog-floor conditions failed. An F3 v2 may be pre-registered (section 7) |

**Independent audit.** A separate review rebuilt every figure from the raw files (scores, mapping, baseline scores, check files, run logs) and found no mismatches; the decision follows mechanically from the four pre-registered rules. It confirmed the pre-run note was committed before the first call with the same contents, all 18 trace IDs match the run files, and all 18 root runs are present in LangSmith with success status. The run files' "pending" trace status is by design; the earlier "delivered" status was the local exporter's acknowledgement, now confirmed by a LangSmith query.

**Scorer consistency.** The blind baseline re-score differed from the official scores on N-01 (tone not marked) and N-08 (contract failure not visible from the post text). Official scores stay authoritative.

**Limits.** Blinding order can't be proved from file times (access time is not a read log, and the time scoring finished was not recorded), though the times fit the sequence. Several baseline posts had been seen in earlier packets. One sample per case at temperature 0.

**What we learned.** The placement rule fixed every formatting slip, but its side effects were the largest of any fix: three new critical descriptor failures, blog citations down from 9 to 5, the first ads failure, and slower calls. The audit also found that F3 posts used no emoji or exclamation marks, against 6 of 9 baseline posts for each; the 15 baseline cases F3 did not touch still use them. A one-paragraph LinkedIn-only change appears to have shifted the whole output. That is an observation from one sample per case, not proof. The citation failures all landed on titles, subject lines and headlines, the fields the baseline's field-coverage rule names.
