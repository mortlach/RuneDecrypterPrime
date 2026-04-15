# Fixed-Instance Solver Development v1

Authoritative contract:

- `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_solver_development_v1_spec_2026-04-14.md`

This branch is the analysis-first next phase built on the frozen fixed `20`-job
panel.

Frozen inputs:

- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

Primary trio:

- `1511`
- `611`
- `1111`

Cross-check case:

- `1411`

Required outputs:

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

Non-goals:

- no live runs
- no benchmark expansion
- no stop-rule promotion
- no family-quality-vN branch
- no solver/runtime tuning before the baseline and audits exist
