# No-WLI Fixed-Instance Solver Development v1

This is the authoritative contract for the first solver-development phase built
on top of the frozen fixed-instance panel.

It supersedes the completed infrastructure stream as the active no-WLI working
contract.

Completed infrastructure baseline:

- `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_mode_v1_spec_2026-04-08.md`

## Goal

Use the frozen fixed panel to answer:

- for one fixed ciphertext instance, what changes in the pipeline actually
  improve solving, and where does the good path get lost?

This phase is analysis-first.
It does not start with solver mutation.

## Frozen inputs

Use these exact retained packs as the benchmark basis:

- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

Do not auto-discover a later bundle.
Do not let the benchmark basis drift.

## Benchmark roles

Primary tuning trio:

- `1511`
  - positive control
- `611`
  - middle unsolved case
- `1111`
  - conversion-failure case

Cross-check case:

- `1411`
  - useful but caveated

`1411` must not be treated as an equal first-line tuning target in v1.

## Fixed definitions

### Focus family

Use exactly:

- `focus family = family of the top stage35-admitted row in that run`

This is not the same as:

- dominant mapped stage35 family
- final-best family

Those must remain separate fields.

### Stage35 count fields

Always keep these three fields separate:

- `archive_seed_row_count`
- `best_stage35_seed_row_count`
- `space_map_stage35_row_count`

They must never be collapsed into one generic stage35 count.

### Solved-run caveat handling

Solved runs with archive-side stage35 rows but zero family-mapped stage35 rows
are valid retained cases, not missing-data failures.

Explicit caveat cases:

- `1411/7003`
  - `archive_seed_row_count = 6`
  - `best_stage35_seed_row_count = 0`
  - `space_map_stage35_row_count = 0`
- `1511/7001`
  - `archive_seed_row_count = 5`
  - `best_stage35_seed_row_count = 0`
  - `space_map_stage35_row_count = 0`

### Trust-field naming

- planning/spec text may say `retained trust-related fields`
- extractor and output contracts must use the exact retained field names

## Required outputs

Write outputs under:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/<timestamp>__fixed_instance_solver_development_v1/`

Required v1 outputs:

- `panel_baseline_rows.jsonl`
- `instance_summary_rows.jsonl`
- `instance_search_matrix.csv`
- `fixed_instance_solver_baseline_cases.md`
- `1111_conversion_compare_rows.csv`
- `1111_conversion_failure_audit.md`
- `1511_positive_control_compare_rows.csv`
- `1511_positive_control_audit.md`
- `611_middle_case_compare_rows.csv`
- `611_middle_case_audit.md`
- `1411_caveat_and_use_note.md`
- `candidate_solver_change_shortlist.md`

## Required baseline-row fields

Each completed-run baseline row must include:

- instance id
- source key seed
- search seed
- run type
- best match ratio
- solved / unsolved / stalled
- best stage
- `archive_seed_row_count`
- `best_stage35_seed_row_count`
- `space_map_stage35_row_count`
- retained trust-related fields
- stage35 selected or not
- family summary if available
- caveat flags
- run provenance

## Required comparison-table fields

The per-run comparison tables for `1111`, `1511`, and `611` must preserve:

- best match ratio
- best stage
- `archive_seed_row_count`
- `best_stage35_seed_row_count`
- `space_map_stage35_row_count`
- focus family
- dominant mapped stage35 family
- final-best family
- retained trust-related fields
- baseline source or lane if available
- key stage35 notes

## Required behaviour

- deterministic row ordering under input reordering
- no silent dropping of runs with partial family mapping
- no silent dropping of archive-only stage35 runs
- markdown summaries must keep:
  - the primary trio
  - the `1411` caveat
- the branch must stay analysis-first until the shortlist exists

## Planned analysis branch

Branch home:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/`

Planned documentation:

- `SPEC.md`
- `EXPERIMENT_PLAN.md`

Planned implementation files for the later coding pass:

- `extract_fixed_instance_solver_development_v1.py`
- `tests/tools/test_no_wli_fixed_instance_solver_development_v1.py`

## Explicit non-goals

- no new broad fixed panel
- no live-seed collection
- no stop-rule promotion
- no promoted family-quality head
- no new family-quality-vN branch
- no benchmark expansion
- no blended stage35 headline metric
- no solver/runtime tuning before the baseline and audits exist

## Forbidden shortcuts

- no latest-bundle discovery
- no collapsing the three stage35 count fields
- no drifting focus-family definition
- no using vague trust wording in concrete outputs
- no treating `1411` as an equal first-line tuning case
- no broad config sweep before the shortlist exists
