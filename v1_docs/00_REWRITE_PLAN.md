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
python tutorials/v1/run_pretty_print_release.py
```

Current printout review command:

```text
python tutorials/v1/run_pretty_print_output_review.py
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
  beginner, extended, showcase, and advanced examples.
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
- `development/adding_a_cipher.md`
- `development/adding_a_scorer.md`
- `development/adding_a_tutorial.md`
- `development/docs_style.md`

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

## Immediate Next Slice

Finish Phase A and continue Phase B/C:

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
