# V1 cleanup plan and local-agent handoff

Status: planned for local implementation. Owner decision: include a practical
repository-wide Ruff cleanup in V1 preparation. This supersedes the earlier
blanket deferral of that work. No cleanup or Ruff inventory has been run as part
of writing this plan.

## Where this fits

The remaining sequence is:

1. Finish active documentation and reconcile stale status notes.
2. Apply the bounded Ruff and formatting cleanup described below.
3. Close the risk-based test/fixture review and code/release/OPSEC reviews;
   repair concrete findings.
4. Obtain explicit authorisation for final broad release proof.
5. Publish V1 with the agreed artefacts, release notes and branch handoff.

The Ruff work can start independently while documentation is being prepared,
provided edits do not overlap. It does not require another architecture review.
See [V1 release status](v1_release_status.md) for the complete outstanding list
and [documentation style](docs_style.md) for prose and comment changes.

## Local agent: start here

Work on `mortlach/RuneDecrypterPrime`, using `prelease/v1-release-readiness` as
the integration source. Read `AGENTS.md` and the referenced V1 authority before
editing. Check the actual branch, remote head and local changes. Preserve
uncommitted work. Local and connector-published commits can have different
ancestry with identical trees; do not reset or force-push to hide that difference.
Use a separate work branch or worktree if needed.

The immediate task is Ruff/code-style cleanup, not all remaining release work.
Complete the ordinary low-risk changes and publish reviewable commits using the
existing authorisation. Do not merge/tag a release, launch campaigns or run
broad suites as part of this handoff.

## 1. Establish the actual starting point

Inspect `pyproject.toml`, any additional lint configuration and existing tooling.
Record the Ruff version used and use one version throughout the cleanup.
The configuration inspected when writing this plan targets Python 3.11, excludes
`src/rdp/ciphers/dev`, and has per-file ignores including E402, E701/E702,
E731/E741 and F401/F811/F841. These exceptions are review inputs, not permission
to delete imports or duplicate definitions blindly.

Run read-only lint and formatter checks on maintained tracked Python files.
Include runtime source, tests, tools, tutorials, solving/cipher-development
programs and maintained root scripts. Review the existing excluded development
area separately for relevance; do not quietly treat it as cleaned. Do not walk
virtual environments, generated output, large asset packs, vendored code or
historical snapshots merely because they are present locally.

Summarise findings by rule and area, with representative examples and the
formatter's proposed scope. Inspect suppressed findings in targeted files as
needed. Do not disable all ignores globally and mistake the resulting noise
for a new release requirement.

Keep this inventory short. A diagnostic count is useful; a new lint registry
or a prose review of every occurrence is not. We have not yet measured the
amount of work, so do not promise that every finding is mechanical.

## 2. Fix the straightforward cases

Begin with a representative batch, then carry the approach across maintained
folders. Keep formatting-only changes separate from manual lint repairs.
Typical work includes whitespace/layout, expanding compressed statements and
removing genuinely unused local code where its evaluation has no side effects.

Preview fixes and review the diff. Use only the intended rules and files for a
batch. Start with fixes Ruff classifies as safe, but inspect them too: an unused
import can still perform registration, and an apparently unused expression can
still matter. Do not use blanket unsafe fixes.

Use the formatter where it improves consistency, retaining deliberate formatting
for rune/index fixtures and readable numerical tables. Preserve comments,
explanations and scientific data exactly unless a separate reviewed change is
needed. Avoid mixing a global formatter sweep with all manual fixes in one commit.

Do not enable every Ruff rule, add naming/docstring regimes, change the Python
minimum or introduce new lint infrastructure during cleanup. Additional rules
such as import sorting need a clear benefit and a separate review of import
order; they are not automatically required by this plan.

## 3. Review the cases that can change behaviour

Handle each concrete risk in its owning area:

- Imports and re-exports: preserve the 141 public paths, 32 root exports,
  registration effects and required import order.
- Duplicate definitions: check whether they are overloads, abstract declarations
  or real duplicates before changing anything.
- Unused assignments: preserve calls that validate, register or otherwise do work.
- Lambdas and local renames: check binding, signatures and introspection where
  relevant. Do not rename public parameters or identifiers for cosmetic reasons.
- Scientific code: preserve arithmetic order, RNG calls/seeds, solver settings,
  fixtures, oracle use, result thresholds and stable serialised values.

Remove or narrow an ignore when the reason for it has actually been resolved.
Keep a necessary exception with a short explanation; do not replace it with a
broader suppression to obtain a green summary.

If a finding exposes a bug, isolate the fix from formatting and verify the
behaviour it changes. Routine repairs within the accepted contract can proceed.
Ask only where the fix needs a new API/scientific decision or conflicts with
accepted behaviour. Continue independent cleanup while that decision is open.

## 4. Verify proportionately

For formatting-only batches, use syntax checks, an AST comparison where useful,
Ruff checks and diff review. An unchanged AST supports preservation of logic;
it does not establish unchanged source hashes or line-dependent behaviour.
Check consumers of exact source or fixture identity where relevant rather than
regenerating evidence blindly.

For manual lint repairs, use the smallest existing tests that exercise the
concrete risk, plus relevant import/public-surface checks when imports change.
Inspect expected runtime before starting. Do not add tests that simply mirror
formatting or count files.

No full pytest, CI-light suite, full-assets proof, long solver test, benchmark or
qualification campaign without a separate explicit owner request. Do not run
all tutorials merely because comments or imports were tidied. Check automatic
CI triggers before publication and retain the established commit-level skip
for broad CI where needed; do not silently alter workflow policy.

## 5. Close and hand back

Rerun the agreed lint/format checks on the maintained scope. Report what is
clean, what remains excluded or intentionally suppressed, and any unresolved
behavioural finding. The goal is useful consistency and fewer unnecessary
exceptions, not a claim that every rule passes across every historical file.

Use a few reviewable commits grouped by area and purpose. Update any directly
affected docs or tooling, and publish the branch without force-pushing. Provide
the GitHub link, commit IDs, checks actually run and remaining decisions. Keep
runtime evidence separate from lint success.

The final release proof stays at the end of the wider V1 sequence, after the
remaining documentation and reviews have settled.

## Still outside this work

AN1–AN4 remain closed. No API redesign, package reshuffle, new cipher/solver/scorer
families, broad scientific retuning, new tutorial machinery or historical evidence
rewrite. P7/C7 campaigns and refinement of the accepted robustness REVIEW cases
remain follow-up work as recorded in the roadmap.
