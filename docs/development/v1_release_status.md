# V1 release status and remaining work

Status reviewed: 2026-09-05.

We are close to a V1 release candidate. The architecture and package migration
are closed, and the getting-started route has now had its second editorial
pass. The remaining work is documentation, a bounded test-system and release
review, public-release hygiene, and final proof on the version we intend to ship.
There is no agreed V2 feature plan in the reviewed material.

## Current source

- Repository: `mortlach/RuneDecrypterPrime`.
- Working branch: `prelease/v1-release-readiness`.
- Reviewed published implementation: [`682e9f0`](https://github.com/mortlach/RuneDecrypterPrime/commit/682e9f0f4f38d730016e7123d1c76866bb412c32).
- Equivalent local implementation commit: `3f9a389bf0d48351a572c567c73b0e1435b0ec14`.
- Shared tree: `62d61c0568795b1f139a89498eb1c82f0e5a5494`.

Publication through the GitHub connector produced different commit ancestry
with the same files. This status note is a later documentation change, not a
new implementation baseline or release tag.

## What is complete

AN1–AN4 are closed: public contracts, API implementation and package organisation.
The installed namespace is `rdp`; normal callers use `from rdp import api`.
The accepted surface remains 141 public paths and 32 root exports, with
`api.run`, `api.encrypt` and `api.decrypt` as the ordinary operations. We do not
need AN5 or another architecture pass. The [authority record](../release_contracts/v1/V1_AUTHORITY_AND_DECISIONS.md)
contains the closure evidence and the limits on further changes.

The reader-experience work is implemented and published:

- Ten getting-started files explain RDP concepts and useful alternatives where
  they first appear, including custom key development.
- All 26 existing programs remain in `examples/`, with their assets, approximate
  runtimes and use of known answers described in the catalogue.
- Repeated source-path setup has been removed from the examples. The runner
  launches modules and each script checks its own expected outcome.
- The default `RELEASE` selection contains all ten starting files and three
  worked examples. Bundled, full-asset and qualification selections are separate.
- Maintained project folders have local README introductions. The main reader
  route, key-space, solver and scoring explanations have been improved.
- The second prose pass establishes the agreed `mortlach` voice. The
  [style guide](docs_style.md) records it for later docs and folder-README work.

These changes improve the route into the software. They do not mean every
remaining reference page has been checked and reconciled. See the
[reader-experience implementation record](rdp_reader_experience_plan.md).

## Work remaining for V1

### 1. Finish the documentation pass

Read the active guides, reference and extension pages against current source.
Finish promoting useful `v1_docs/` material into canonical `docs/`, keeping
historical evidence clearly identified. Preserve pages still used by contract
tests until their consumers have been dealt with deliberately.

Apply the agreed voice to the remaining prose and folder READMEs: explain what
we are doing, why the choice matters and a few useful alternatives. Keep the
technical meaning, use correct grammar, and leave humour out when unsure.
This does not authorise renaming public identifiers or changing report values.

Reconcile old status notes and links. Concrete examples found in this review:

- [Issue #4](https://github.com/mortlach/RuneDecrypterPrime/issues/4) remains open,
  although the starting route is implemented. Its old school/teaching framing
  was superseded by the later owner decisions. Update and close it with the
  implementation evidence during bookkeeping.
- Earlier authority and index text still calls tutorial tiering deferred.
- The original onboarding specification still contains an unpushed completion
  condition, superseded by the owner's publication instructions.
- The release acceptance page calls the default runner command a full-profile
  command, while the runner defaults to `RELEASE`. Explain selection explicitly.

Finish the user-facing release notes and forum/release announcement once the
actual release contents and limitations are settled.

### 2. Close the risk-based test and fixture review

This remains agreed V1 work under decision V1-DEC-010. I found no closure record
for the complete review. Existing passing test runs do not establish that the
test organisation and retained fixtures have been reviewed.

Account for every test at inventory level. Review release-critical contracts
and retained experimental capabilities in detail; group repetitive low-risk
cases. Decide which tests and fixtures to retain, repair or retire, and make
asset, platform and long-run selections clear. Retain campaign tests where they
protect reusable framework behaviour or explicitly retained scientific evidence.

The tutorial manifest/hash machinery has already been simplified. Check for
remaining unnecessary coupling without weakening full-asset, native binary,
immutable corpus or scientific-fixture integrity. Do not create a new catalogue
framework or write a prose review of every individual assertion.

### 3. Finish the bounded code and public-release review

Check for concrete release blockers across source, installer, packaging,
workflow selections and supported examples. Reuse the accepted AN1–AN4 evidence;
do not repeat the migration inventories or reopen the public architecture.

The owner has requested an OPSEC/publication check. Its completion has not been
established. The proposed check covers credentials, personal or internal notes,
machine-specific paths, unintended logs and generated files, archive contents,
and intended attribution in source and Git metadata. Check distribution and
asset notices as part of preparing the public artefacts. Report any actual
finding by category without copying sensitive values into public notes.
History rewriting or credential rotation would be a separate concrete action,
not an automatic consequence of this review.

### 4. Prove the final release candidate

Once the content is settled, obtain explicit authorisation for broad execution.
Then record evidence for the exact final source and artefacts:

- Windows and Ubuntu/Linux, formally on Python 3.11;
- clean installation, native imports, wheel/sdist construction and isolated
  installed-package behaviour;
- full V1 assets, complete pytest and the declared release tutorial groups;
- the `RELEASE` and `FULL_ASSET_EXAMPLES` selections, with any skips or accepted
  limitations explained;
- a final lightweight review pack regenerated from that same head.

The review pack is separate from the curated scientific-evidence release ZIP.
Qualification campaigns are excluded from ordinary release proof.

### 5. Publish V1

The agreed release set is the production wheel, production sdist, full V1 asset
package and curated source/scientific-evidence ZIP retaining Pack 09. Verify
that links, manifests and notes describe the actual delivered files.

The agreed branch model is released versions on `main`, followed by `develop`
for ongoing integration. Finalise the integration branch, merge/tag and publish
only as the release step. Do not reset branches merely to make their names
match an older plan.

## Held back deliberately

| Item | Current position |
| --- | --- |
| New P7/C7 campaigns | Follow-up work using `cipher_development/periodic_columnar_staged/`. The existing qualification and warm-start example are retained. Choose the next question, budget, stop rule and acceptance before starting another campaign. |
| Robustness recipe refinement | `mono_ga.19` and `generic_map_multiply_beam.12` remain accepted, non-blocking REVIEW cases. Their recipe limitations are disclosed; they are not reopened API defects. |
| Broad scientific retuning | Separate from documentation and release cleanup. |
| New ciphers, solvers, scorer families or public-API redesign | Outside V1 closeout unless a concrete blocker requires an owner decision. |
| Repository-wide Ruff/code-style cleanup | Deferred. The agreed prose cleanup is a different task. |
| More starting examples | Add only for a demonstrated gap, useful comparison or supported feature; no target file count or general course. |
| Tutorial CLI, installed tutorial namespace, new tutorial registries/hashes | Outside the agreed design. Keep the simple module route and explicit runner groups. |
| General Python or cryptography curriculum | Outside this project's onboarding scope. |
| Long qualification in ordinary checks | Excluded. Availability of the tooling does not authorise a run. |

## What has actually been verified

AN4 records successful local/full-asset, installed-package and cross-platform
proof for its accepted baseline. The first onboarding migration later recorded
1,734 passed, 27 skipped and 17 full-asset deselections in CI-light. Neither is
new full proof of the current head.

The reader-experience follow-up used targeted checks and five worked examples.
The final prose pass checked Python syntax, unchanged logic apart from four
printed labels, local links and whitespace. It ran no searches or test suites.
The recent editorial commits skipped broad automatic CI; workflow policy was
not changed. The clean-install instructions have been supplied, but the user's
result has not yet been reported here.

No tests, campaigns, security scan or release build were run for this status
review. No unresolved item above should be read as a discovered runtime defect.

## Suggested order

Finish docs and status reconciliation, then close the bounded test/fixture and
public-release reviews. Fix concrete findings, settle the release notes, run the
explicitly authorised final proof and publish V1. Future scientific work can
then proceed without extending the release indefinitely.

The evidence for this summary is the current source, recent owner decisions,
the [resolved decisions](../release_contracts/v1/v1_resolved_decisions.csv),
[release acceptance gates](../release_contracts/v1/V1_RELEASE_ACCEPTANCE_GATES.md),
[onboarding deferrals](../release_contracts/v1/V1_RR_ONBOARDING_AND_EXAMPLES_SPEC.md#17-follow-up-and-explicitly-deferred-work)
and [active roadmap](../ROADMAP.md). Older planning language is interpreted in
light of the later owner corrections, including the technically capable audience
and explicit restriction on broad and long tests.
