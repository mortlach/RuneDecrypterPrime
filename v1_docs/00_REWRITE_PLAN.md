# V1 documentation rewrite plan

Status: working plan

## Purpose

Build a clear V1 documentation set for Rune Decrypter Prime.

The target reader is an interested high-school student through to an expert
integrator. The first path should be easy to run and understand. Deeper pages
should explain the real system without hiding uncertainty, truth data, solver
limits, or report-only diagnostics.

## Ground Rules

- Work in the pure release tree: `pure_release_repo/RuneDecrypterPrime`.
- Keep this folder clean; do not copy old planning folders into it.
- Treat `docs/` and `local_archive/.../planning` as source material, not as
  authority.
- Document only behavior that exists in the current clean tree.
- Prefer short, direct pages over sprawling reference dumps.
- Beginner docs use direct Python files, not environment variables or CLI-heavy
  controls.
- Code examples must be checked before they become public docs.

## Current Anchors

Current beginner commands:

```text
python install.py
python tutorials/v1/run_tutorials.py
```

Current printout review setting:

```python
CONSOLE_OUTPUT = ConsoleOutput.FULL
```

Current first-class report/display surfaces:

```text
RunSpec
RunResult
SolverReport
ScorerReport
RDP display summary
```

Current important tutorial/report policy:

- Reports should print `encoding_dir` where plaintext is interpreted.
- Known truth/oracle data must be visible when used.
- Report-only diagnostics must not affect ranking.
- Tutorial acceptance is evidence for the tutorial, not a hidden production
  ranking rule.
- Public V1 tutorial runners should use visible constants in the runner, not
  shell-controlled tutorial behavior or separate tutorial config files.
- `tutorials/v1/` should eventually hold all working V1 tutorials, including
  beginner, extended, partial recovery, and advanced examples.
- Tutorial docs should be easy to update when tutorials are added: one selected
  runner list, one metadata/manifest story, and one cross-check step.

## Proposed Reader Lanes

### 1. Use RDP

Goal: get a beginner from install to a successful tutorial run.

Candidate pages:

- `install.md`
- `tutorials.md`
- `troubleshooting.md`
- `outputs.md`

Keep these pages short. Avoid special shell setup, separate tutorial config
files, command-line tutorial control, and old setup/preflight tooling.

### 2. Understand RDP

Goal: explain what RDP is and why it is designed this way.

Candidate pages:

- `core_design.md`
- `runes_and_text.md`
- `runs_reports_and_artifacts.md`
- `tutorials_as_evidence.md`

Source material:

- `docs/expert/design_philosophy.md`
- `docs/expert/component_model.md`
- `docs/expert/stability_surface.md`
- archived `planning/projects/rdp_v1` governance and architecture notes

### 3. Extend RDP

Goal: help contributors add or review behavior without silent drift.

Candidate pages:

- `development/testing.md`
- `howto/add_cipher.md`
- `howto/add_solver.md`
- `howto/add_scorer_lane.md`
- `development/adding_a_tutorial.md`
- `development/docs_style.md`

Lane split:

- `coder/`: maps, architecture, pipelines, and support boundaries
- `howto/`: concrete contributor task recipes
- `development/`: testing, docs-style, and tutorial policy material

Source material:

- `docs/howto/`
- `docs/tests_docs/`
- `docs/development/docs_style.md`

### 4. Reference

Goal: exact descriptions of stable surfaces after the reader path is settled.

Candidate pages:

- `reference/run_spec.md`
- `reference/ciphers.md`
- `reference/solvers.md`
- `reference/scorers.md`
- `reference/reports.md`
- `reference/telemetry.md`
- `reference/assets.md`
- `reference/tutorial_manifest.md`

Do this after the beginner path and core design narrative are stable.

## Phase Plan

### Phase A: Structure And Source Inventory

Deliverables:

- This plan.
- A source map of current pages to reuse, rewrite, archive, or ignore.
- A cross-check ledger that records staged-docs claims against current code.
- A remaining-work checklist for promotion from staging docs to public docs.
- A decision on whether `v1_docs/` becomes the new public docs tree or is merged
  back into `docs/` after review.

Exit condition:

- We know which existing docs are source material and which are stale.

### Phase B: Beginner Path

Deliverables:

- `install.md`
- `tutorials.md`
- `troubleshooting.md`
- `outputs.md`

Exit condition:

- A new user can install and run the pretty-print tutorial gate using only this
  folder.

### Phase C: Core Design

Deliverables:

- `core_design.md`
- `runes_and_text.md`
- `runs_reports_and_artifacts.md`

Exit condition:

- The docs explain RDP's philosophy, text encoding directions, RunSpec,
  SolverReport, ScorerReport, display summaries, truth/oracle policy, and
  report-only diagnostics plainly.

### Phase D: Tutorial And LP Explanation

Deliverables:

- `tutorials_as_evidence.md`
- `lp_examples.md`
- a transition plan for aligning all working `tutorials/v1/` tutorials with the
  pretty-print runner and tutorial manifest

Exit condition:

- Tutorials, solved LP examples, source labels, known plaintext, and oracle use
  are clearly separated.
- The docs explain how future tutorials are added without hand-editing stale
  lists in several places.

### Phase E: Contributor Docs

Deliverables:

- `development/testing.md`
- `development/adding_a_tutorial.md`
- initial contributor pages for ciphers/scorers if current code supports them

Exit condition:

- A contributor has a safe path for small changes and tests.

### Phase F: Reference Pages

Deliverables:

- Reference pages for stable V1 concepts.

Exit condition:

- Reference pages document current behavior and link to tests/contracts where
  useful.

## Decisions Recorded

1. `v1_docs/` is a staging folder for now.
2. Beginner docs should use plain `python`, not a machine-specific interpreter
   path.
3. The old `docs/` tree stays in place while the new documentation is drafted.
4. Core coder documentation is Markdown-first for this phase. Sphinx, autodoc,
   autosummary, and Doxygen may be added later, but generated documentation
   must not define the intended public support boundary.
5. Hand-written docs define the intended support boundary; generated docs
   reflect inspected code. If docs, code, and tests disagree, record or fix the
   mismatch.
6. Generated documentation output belongs outside the repo, for example under
   `run_outputs/docs/`. Source docs live in `v1_docs/`; built HTML, doctrees,
   generated API dumps, coverage reports, and other generated artifacts do not.

## Core Coder Documentation Plan

Status: implementation plan

Scope: `v1_docs/`

Goal: create detailed, maintainable documentation for the core Rune Decrypter
Prime codebase: package structure, public classes, function surfaces, run flow,
extension points, reporting contracts, and tests that protect behaviour.

Done means a reader can open `v1_docs/` and understand:

- what the main RDP packages do
- which classes/functions are intended public surfaces
- how a run moves from input to spec to cipher/key/solver/scorer to reports
- how to add or review a cipher, solver, scorer, or tutorial
- which behaviour is contract-backed by tests
- which internals are intentionally not public API

### Documentation Lanes

The staged docs use these lanes:

| Lane | Purpose |
| --- | --- |
| Beginner/user docs | Short, runnable, friendly first path. |
| Understanding docs | Concepts and design. |
| `coder/` | Codebase maps, architecture, pipelines, and support boundaries. |
| `howto/` | Concrete contributor task recipes. |
| `development/` | Existing policy, testing, and docs-style material. |
| `reference/` | Exact stable contracts and allowlists. |
| Generated docs | Optional later; build output stays outside the repo. |

Do not duplicate `howto/` and existing `development/` pages. Prefer `coder/`
for explanations, `howto/` for task recipes, and `development/` for policy.

### Public API Boundary

Do not imply every importable function is public. Documented objects should be
classified as one of:

- Public V1 surface
- Semi-stable contributor surface
- Internal helper
- Test-only helper
- Legacy / transitional

Start with a narrow, verified public API allowlist and expand only after
inspection. The allowlist lives in `reference/public_api_allowlist.md` and uses
a simple table so tests can check it.

### Work Packages And Intelligence Level

| WP | Work package | Intelligence level | Notes |
| --- | --- | --- | --- |
| WP0 | Record the decision | Low to medium | Mostly planning hygiene; needs release-rule awareness. |
| WP1 | Core package inventory | High | Requires careful code reading and honest "not yet assessed" markers. |
| WP2 | Public API boundary | Very high | Requires judgement about stable support promises versus importable internals. |
| WP3 | Run flow documentation | High | Requires understanding runtime wiring, reports, and separation of responsibilities. |
| WP4 | Spec/config object docs | High | Requires field-level inspection and validation-rule accuracy. |
| WP5 | Pipeline pages | Very high | Cipher/key/solver/scoring boundaries are where silent drift risk is highest. |
| WP6 | Reports, telemetry, and artifacts | Very high | Contract-backed evidence, oracle use, and diagnostic-only claims must be precise. |
| WP7 | Extension docs | High | Must give safe contributor paths without encouraging unsupported edits. |
| WP8 | Docstring policy and targeted annotation | High | Good judgement matters more than volume; avoid low-value comments. |
| WP9 | Cross-check and drift tests | Medium-high | Mostly mechanical once scope is clear, but test claims must not be brittle. |

### First Implementation Slice

The first slice is deliberately small:

- update this plan and `03_REMAINING_WORK.md`
- add `coder/README.md`
- add `coder/module_map.md`
- add `coder/public_api.md`
- add `coder/docstring_policy.md`
- add `reference/public_api_allowlist.md`
- add a focused docs-contract test

Do not generate full-package API docs in this slice.

### WP0 Close-Out

Status: complete for the initial coder-docs implementation.

Recorded decisions:

- source docs are Markdown-first in `v1_docs/`
- Sphinx, autodoc, autosummary, and Doxygen are deferred
- hand-written docs define the intended support boundary
- generated docs reflect inspected code, not the other way around
- generated documentation output stays outside the repo under a root such as
  `run_outputs/docs/`
- the `coder/`, `howto/`, `development/`, and `reference/` lanes have distinct
  jobs
- the public API boundary starts narrow and expands only after inspection

## Immediate Next Slice

Finish Phase A and continue Phase B/C, then build the first core coder-docs
slice:

1. Review and refine `01_SOURCE_MAP.md`.
2. Review and refine `troubleshooting.md`.
3. Review and refine `outputs.md`.
4. Review and refine `runs_reports_and_artifacts.md`.
5. Review and refine `tutorials_as_evidence.md`.
6. Review and refine `lp_examples.md`.
7. Review and refine Phase E contributor docs.
8. Review `02_CROSSCHECK.md` and resolve the tutorial manifest alignment
   question.
9. Review `03_REMAINING_WORK.md` and close or split the listed work.
10. Review and refine initial Phase F reference pages.
11. Plan the tutorial manifest/runner alignment so all working `tutorials/v1/`
    tutorials can be classified and documented as the set grows.
12. Decide when a staged page is ready to replace or redirect an old `docs/`
   page.
13. Establish the `coder/` lane with a module map, public API boundary, and
    docstring policy.
14. Add docs-contract tests for the initial public API allowlist and coder-doc
    hygiene.
