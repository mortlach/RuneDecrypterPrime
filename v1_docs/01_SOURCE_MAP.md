# V1 documentation source map

Status: staged Phase A inventory

This map says how the current documentation should feed the V1 rewrite. It is
not a copy plan. Old pages and archived planning notes are source material to
read, simplify, verify against the current tree, and rewrite.

## High-Level State

The live `docs/` tree contains useful V1 material, but it mixes several eras:

- beginner setup pages
- architecture and expert explanations
- tutorial pages from older tutorial formats
- release contracts and traceability files
- test documentation
- appendices and glossary material
- stale indexes and historical workflow pages

The archived planning tree under:

```text
local_archive/repo_prune_h1_2026_06_10/planning
```

is useful for motivation, design history, and decisions that may not be obvious
from code. It should remain read-only and should not be copied into the release
docs.

## Rewrite Buckets

| Source area | Use for V1 rewrite |
| --- | --- |
| `README.md` and `docs/README.md` | Source for the top-level reader path, after the staged pages settle. |
| `docs/INDEX.md` | Likely stale. Replace with a tiny redirect or retire once the new map is ready. |
| `docs/setup/` | Reuse only verified install/build concepts. Rewrite beginner install around `python install.py` and the pretty-print runner. |
| `docs/guides/quickstart.md` | Source for beginner flow, but rewrite heavily because the tutorial runner policy changed. |
| `docs/guides/troubleshooting.md` | Source for likely failure cases, but rewrite heavily to remove old setup assumptions. |
| `docs/guides/outputs.md` | Source for `outputs.md` and `runs_reports_and_artifacts.md`. Verify against current display and log behavior. |
| `docs/expert/design_philosophy.md` | Strong source for `core_design.md`. Simplify language before promoting. |
| `docs/expert/component_model.md` | Strong source for RunSpec, RunResult, solver, scorer, and report explanations. |
| `docs/expert/stability_surface.md` | Strong source for public/stable/moving surface boundaries. |
| `docs/guides/philosophy.md` | Source for beginner-friendly philosophy if it still matches current contracts. |
| `docs/guides/pipeline.md` and `docs/architecture/pipeline.md` | Source for run flow diagrams and pipeline explanation. Consolidate to one V1 narrative. |
| `docs/architecture/` | Use selectively for reference pages after beginner/core docs are stable. |
| `docs/howto/` | Source for future contributor pages. Do not promote until code examples are checked. |
| `docs/tests_docs/` and `docs/tests/` | Source for contributor testing docs. Keep separate from beginner install. |
| `docs/tutorials/` | Historical tutorial source. Rewrite around `tutorials/v1/*.py` and the two current runners. |
| `docs/release_contracts/v1/` | Contract evidence. Link sparingly from contributor/reference docs, not beginner pages. |
| `docs/v1_traceability/` | Contract/enum evidence. Keep out of the beginner path. |
| `docs/appendices/glossary.md` | Source for a short glossary after the main pages have stable terms. |
| `docs/appendices/telemetry_schema.md` | Source for telemetry reference only. |
| `docs/user/README.md` | Source for public reader lanes if current. Verify before reuse. |
| `docs/repo/structure.md` | Source for contributor orientation if current. |

## Archived Planning Sources

Use these archived areas for context, not copy:

| Archive area | Useful context |
| --- | --- |
| `planning/projects/rdp_v1/00_CURRENT_STATE.md` | Historical current-state snapshot and why V1 needed a cleaner release shape. |
| `planning/projects/rdp_v1/01_WORKSTREAM_INDEX.md` | Workstream names and motivation. |
| `planning/projects/rdp_v1/02_OPEN_QUESTIONS.md` | Old uncertainties to check against current code before documenting. |
| `planning/projects/rdp_v1/03_DOCUMENT_MAP.md` | Historical map of design notes and support material. |
| `planning/projects/rdp_v1/04_ACTIVE_RUNBOOK.md` | Process history only; do not turn into user instructions. |
| `planning/projects/rdp_v1/05_REMAINING_WORK.md` | Historical gap list; verify before reusing. |
| `planning/projects/rdp_v1/10_governance/` | Motivation for transparent reports, explicit scope, and no silent drift. |
| `planning/projects/rdp_v1/20_active_plans/` | Historical implementation intent; check against current source before documenting. |
| `planning/projects/rdp_v1/40_supporting_reference/` | Deep background. Use only when a current docs page needs origin context. |
| `planning/projects/no_wli/` | Useful background for WLI/no-WLI and damaged-text scorer discussion. Keep out of beginner docs. |
| `planning/projects/p13_real_ciphertext_campaign/` | Real-ciphertext campaign context. Use later for LP/example pages if still relevant. |
| `planning/projects/benchmark_campaign_v1_1/` | Benchmark/community-campaign history. Not part of the first V1 beginner path. |

## Current Staged Page Targets

| Staged page | Primary sources | Notes |
| --- | --- | --- |
| `02_CROSSCHECK.md` | current code, runner files, API contracts | Ledger for current staged-docs verification and mismatches. |
| `install.md` | `docs/setup/installation.md`, current `install.py`, current tutorial runners | Keep plain and short. |
| `tutorials.md` | `tutorials/v1/`, `docs/tutorials/`, release tutorial contracts | Must reflect the final pretty-print tutorial list. |
| `troubleshooting.md` | `docs/guides/troubleshooting.md`, current install/tutorial behavior | Rewrite around the simple path; no old preflight flow. |
| `outputs.md` | `docs/guides/outputs.md`, current display/log output | Explain where logs go and what summaries mean. |
| `core_design.md` | `docs/expert/design_philosophy.md`, `component_model.md`, `stability_surface.md`, current API contracts | Already started; refine against code. |
| `runes_and_text.md` | current rune encoding helpers, display tests, WLI behavior | Must explain direction, multi-letter runes, and canonical display. |
| `runs_reports_and_artifacts.md` | RunSpec/RunResult/SolverReport/ScorerReport code and tests | Next core-design page. |
| `tutorials_as_evidence.md` | tutorial manifests, release contracts, current runners | Separate tutorial evidence from production ranking. |
| `lp_examples.md` | `Tutorial_LP_Welcome_Pilgrim_Solve.py`, `solving/solved_lp/`, LP source catalogue | Explain solved LP examples without turning workbooks into beginner setup. |
| `development/testing.md` | `tests/`, `tests/conftest.py`, CI workflow contracts | Contributor testing only; not beginner setup. |
| `development/adding_a_tutorial.md` | current pretty-print tutorials, runner contracts, tutorial report helpers | Explain the expected tutorial shape. |
| `development/docs_style.md` | staged docs policy, old docs playbook | Keep V1 docs plain, checked, and honest. |
| `reference/run_spec.md` | `src/rdp/api/run_spec.py` | Stable input contract summary. |
| `reference/reports.md` | `solver_report.py`, `scorer_report.py`, `display.py` | Stable report/display vocabulary. |
| `reference/artifacts.md` | `artifact_agreement.py`, `run_artifact_manifest.py` | Known artifact paths and classifications. |
| `reference/tutorial_runners.md` | `run_tutorials.py`, runner contract tests | Runner ownership and current mismatch notes. |
| `reference/tutorial_manifest.md` | `tutorial_manifest_v1.json`, pretty runner list, tutorial contract tests | Target metadata policy for a growing tutorial set. |

## Do Not Promote Directly

Do not promote these into public V1 docs without heavy rewrite:

- old setup/preflight pages
- old tutorial pages that do not match the pretty-print tutorials
- planning runbooks
- generated benchmark results
- local archive notes
- release handoff material
- pages that require special shell setup for a beginner path

## Open Checks

- Confirm whether `docs/INDEX.md` should become a redirect-style page or be
  removed when `v1_docs/` is promoted.
- Re-check every staged command before replacing old docs.
- Cross-check final pretty-print tutorial list against the current runner before
  release.
- Decide how much release-contract evidence belongs in public docs versus
  contributor/reference docs.
