# Active project schema v1

Status: active
Work status: done
Project: project_workflow

## Standard front-door files for active projects

Every active project should aim to have:

- `00_CURRENT_STATE.md`
- `01_WORKSTREAM_INDEX.md`
- `02_PROJECT_DEFINITION_AND_AGENT_RULES.md` or current project-specific rules file
- `03_DOCUMENT_MAP.md`
- `04_ACTIVE_RUNBOOK.md`
- `05_REMAINING_WORK.md`

Project-specific front-door equivalents are acceptable when the project already
has a stable specialised reading model.
For example, an experiment-heavy upstream method home may keep
`01_EXPERIMENT_INDEX.md` and `02_OPEN_QUESTIONS.md` instead of renaming them.

Optional if useful:
- `06_STATUS.md` or project-specific cut-over/status note
- `07_DECISIONS.md` if decisions are substantial enough to deserve their own file

## Standard subfolder shape for active projects

Active projects should converge toward:

- `10_active_plans/`
- `20_specs_and_analysis/`
- `30_status_and_results/`
- `40_supporting_reference/`
- `95_evidence_snapshots/`

Historical cutover/archive material should live outside the active home under:
- `planning_old/projects/<project>/`

## Interpretation

### `10_active_plans/`
Current planned work and near-term execution planning.

### `20_specs_and_analysis/`
Contracts, specs, analysis notes, method notes, design logic.

### `30_status_and_results/`
Status ledgers, run logs, result notes, progress summaries.

### `40_supporting_reference/`
Secondary material:
- support matrices
- maintainer notes
- future-method references
- integration history
- preserved useful legacy notes

### `95_evidence_snapshots/`
Direct code/test evidence snapshots only.

## Important rule

Not every active project must populate every subfolder equally.
The point is consistency of shape, not identical volume.
