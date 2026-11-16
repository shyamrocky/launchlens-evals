# Canonical files and workspace boundary

Authority: explicit owner instruction, 2026-11-04; fixture/workspace refinement,
2026-11-10 (America/Los_Angeles).
This is the canonical policy for file placement and the development-workspace
boundary. AGENTS.md links here rather than maintaining another policy copy.

## Choose the destination before creating a file

- docs/: authoritative project documentation, architecture, approved decisions
  and operating instructions.
- src/, tools/, tests/, or existing equivalents: maintained implementation,
  reusable scripts and tests. Do not add directories or abstractions until needed.
- workspace/: continuity notes only, including BUILD_CONTEXT.md,
  IMPLEMENTATION_PROGRESS.md and MEMORY.md. It is Git-ignored and nonauthoritative.
  Keep maintained code, tests and test resources in their normal project locations;
  use the operating-system temporary directory for disposable test copies.

Never use workspace/ as the sole authoritative location for a project deliverable
or maintained implementation.

## Authority and promotion

Workspace notes cannot approve architecture changes. Approval must be reflected
in version-controlled documentation or explicitly provided by the owner. If notes
conflict with approved documentation or the latest explicit owner instruction,
stop the affected work and flag the discrepancy.

When a draft is accepted, promote it to its canonical repository location, update
references and mark the workspace copy as superseded. Maintain one authoritative
version. Do not treat approval of a draft as permission for an unrelated milestone.

## Reproducibility and private runtime artifacts

The application, build, tests, deployment and required safety checks must not
depend on files inside workspace/. Temporary experiments there must not become
required components. Missing development notes must not prevent setup or testing.

Regression fixtures must be minimal, independently authored synthetic examples of
the failure shape. Do not copy saved Writer responses, run checkpoints, receipts
or other protected execution artifacts into version-controlled test fixtures.
Tests must not require those private artifacts.

Keep private source material and execution records protected. Required private
runtime artifacts need an explicit storage and provisioning contract outside
workspace/, documented in docs/ without publishing restricted content. Describe
required locations, access, provisioning and verification, with safe fixtures or
substitutes where appropriate. M0 has no such runtime artifacts; no storage
provider or provisioning implementation is selected by this policy.

## Development memory and sharing

Owner refinement: 2026-11-04. Development memory has three complementary roles:

- workspace/MEMORY.md: persistent, append-only dated discussion summaries,
  including material clarifications, rationale, open questions and next steps.
- workspace/BUILD_CONTEXT.md: concise, mutable current-state summary.
- workspace/IMPLEMENTATION_PROGRESS.md: milestone/implementation status and actual
  verification evidence, with historical results preserved.

The exact read/write triggers are maintained once in
[AGENTS.md](history/AGENTS-before-submission.md#read-and-maintain-development-context). "Update memory"
appends to MEMORY.md only; ordinary authorized work refreshes state/progress when
material changes warrant it. Before handoff, check relevant files for currency.

Summaries must distinguish verified results, assumptions, proposals and explicit
owner approvals; none of these files grants authority over canonical docs or the
owner. Keep entries concise, link to evidence and exclude full transcripts,
routine command dumps, credentials and employer-confidential material. Existing
historical checkpoints may remain in progress; new discussion summaries belong
in MEMORY.md. No prior discussion is claimed to have been recorded verbatim.

Git ignore rules do not protect manual uploads, archives, deployment packages or
prompt content. Inspect what is shared and exclude workspace/, credentials,
confidential material and restricted artifacts unless an explicitly permitted,
reviewed disclosure applies.

## Milestone check

At each milestone, verify that new required code and documentation occupy their
canonical locations and that no runtime, build, test, deployment or required
safety-check dependency on workspace/ has been introduced. Report actual checks
and any limits. Report existing violations before relocating files or changing
historical bindings; this policy is not blanket migration authorization.

## Week 4 public-repo guardrails and build-in-public rules

Authority: explicit owner instruction, November 15, 2026.

These rules apply to material added for Week 4 in launchlens-evals.
Treat every commit as permanently public. The inherited Week 3 history
through d9d5a8659ed74c3f9ae89bd5815d06e9ce82bdd6 is accepted as is
and is not rewritten. The original Week 3 folder and repository remain
unchanged. The earlier private-repository setup decision is superseded.

### Material that stays private

Never commit credentials, .env, API keys or tokens; raw provider requests
or responses; checkpoints; archived packages; request headers or IDs;
authorization records; budget ledgers; per-run accounting; Notion page
IDs; Drive file IDs; local file paths; or trace exports.

Raw evaluation results and outputs stay in ignored evals/results/ and
evals/outputs/. Do not commit other saved Week 3 run data except for the
narrow typed-notes exception below. Reviewer findings may be read locally
to understand failures but must not be copied into the public repository.

Do not publish employer data, code, names or internal details, or personal
information about anyone. This includes notes, screenshots, recordings
and commit messages.

Do not commit course handouts, course notebooks, other students' work or
the Academy reference repository. Link to their authorized sources instead.

### Narrow exception for the owner's typed notes

For Week 4 golden-case inputs only, the owner's own typed PMM notes from
user_notes or session_notes.agent_notes may be used after the owner
confirms each individual note is their own wording and contains nothing
sensitive. Assign a new case ID and bring no other fields or artifacts
from the saved run. Unit-test fixtures must remain synthetic.

### Material eligible for public review

The evaluation runner, synthetic tests, secret-free manifest, baseline
and fix prompts, scoring rubric, pass bars and golden dataset may be
committed after the checks and owner approval below.

Golden cases contain case ID, slice, PMM notes and expected behavior.
A separately curated results file may contain case ID, input, expected
behavior, LinkedIn post, scores, failure category and summary cost and
latency. Exclude trace IDs, request IDs and run IDs.

The report may include reviewed LangSmith screenshots. Raw trace exports
remain private. Public manifests must not disclose private source IDs or
local paths.

### Review and publication

Before every commit, list the exact proposed files, scan them for keys,
IDs, paths, headers and emails, and wait for owner approval. Before
submission, scan the entire Git history the same way.

No push or paid call is authorized without explicit owner approval.
If sensitive material is committed, stop and do not push. For credentials,
rotate at the provider immediately, even if never pushed. Remove sensitive
material from history before pushing; if already pushed, rotate credentials
first, then address history with explicit owner authorization.

### Build in public

Share methods, datasets, real scores, failures, regressions and limitations
honestly. Do not cherry-pick cases or hide unsuccessful fixes.

Label synthetic material, the fictional Coca-Cola Cherry Float launch and
AI assistance. Keep the fictional-launch disclaimer in README and report.
Credit sources, tools and AI coding assistants.

Before sharing screenshots or video, check keys, emails, account and
organization IDs, browser tabs and terminal history; crop or blur sensitive
material.

README must explain the project, setup with the reader's own credentials
using .env.example, and where results are available. Choose a project
license deliberately or state that none is granted. Keep commit messages
short, factual and professional.
