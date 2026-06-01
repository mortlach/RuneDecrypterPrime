# RDP v1 source crosswalk and backlink status — 2026-04-10

Status: active
Work status: done
Project: rdp_v1

## Purpose

This note records the migration-closeout crosswalk for `rdp_v1`.

The goal is not to rescue more material.
The goal is to make the new `rdp_v1` home usable without leaning on:
- `planning/v1/`
- `planning/working/`
- `planning/review/`

## Main old-source pack

Primary old-source cluster:
- `planning/v1/`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/`

Secondary old-source cluster:
- `planning/review/`
- `planning/old/workgin/`
- `planning/old/`
- `planning/old/v1OLD/audit1/`

## Crosswalk status

### Absorbed into the live/spec layers

- `planning/v1/rdp_v1_governance_charter_v3_owner_review_2026-03-10.md`
  -> `10_governance/rdp_v1_governance_charter_v3_owner_review_2026-03-10.md`
- `planning/v1/rdp_v1_campaign_spec_v1_owner_review_2026-03-10.md`
  -> `10_governance/rdp_v1_campaign_spec_v1_owner_review_2026-03-10.md`
- `planning/v1/rdp_v1_refactor_plan_v2_owner_review_2026-03-10.md`
  -> `20_active_plans/rdp_v1_refactor_plan_v2_owner_review_2026-03-10.md`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/CURRENT_PHASE_v1_2026-03-11.md`
  -> `20_active_plans/CURRENT_PHASE_v1_2026-03-11.md`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/CURRENT_RISKS_v1_2026-03-11.md`
  -> `20_active_plans/CURRENT_RISKS_v1_2026-03-11.md`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/rdp_v1_adr_starter_pack_v1_2026-03-11.md`
  -> `20_active_plans/rdp_v1_adr_starter_pack_v1_2026-03-11.md`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/rdp_v1_implementation_plan_v1_2026-03-11.md`
  -> `20_active_plans/rdp_v1_implementation_plan_v1_2026-03-11.md`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/rdp_v1_task_register_v1_2026-03-11.md`
  -> `20_active_plans/rdp_v1_task_register_v1_2026-03-11.md`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/Review_order.txt`
  -> `20_active_plans/Review_order.txt`

These absorbed live/spec duplicates have now been retired from the old
`planning/v1/` surface.

### Absorbed into the supporting-reference layer

- `planning/v1/maintainer_handbook_v2.txt`
  -> `40_supporting_reference/maintainer_notes/37_maintainer_reference/maintainer_handbook_v2.txt`
- `planning/v1/rdp_private_maintainer_handbook_skeleton_2026-03-09.md`
  -> `40_supporting_reference/maintainer_notes/37_maintainer_reference/rdp_private_maintainer_handbook_skeleton_2026-03-09.md`
- `planning/v1/rdp_v1_feature_support_matrix_draft_2026-03-10.csv`
  -> `40_supporting_reference/support_matrices/31_support_matrices/rdp_v1_feature_support_matrix_draft_2026-03-10.csv`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/RDP v1 current-code mapping note_6.txt`
  -> `40_supporting_reference/support_matrices/31_support_matrices/RDP_v1_current_code_mapping_note_6.txt`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/rdp_v1_current_code_mapping_note_template_v1_2026-03-11.md`
  -> `40_supporting_reference/support_matrices/31_support_matrices/rdp_v1_current_code_mapping_note_template_v1_2026-03-11.md`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/support-to-test map_7.txt`
  -> `40_supporting_reference/support_matrices/31_support_matrices/support-to-test_map_7.txt`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/support_matrix_cell_meanings 5.txt`
  -> `40_supporting_reference/support_matrices/31_support_matrices/support_matrix_cell_meanings_5.txt`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/findings_register.csv`
  -> `40_supporting_reference/support_matrices/31_support_matrices/findings_register.csv`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/change_workflow_4.txt`
  -> `40_supporting_reference/support_matrices/31_support_matrices/change_workflow_4.txt`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/Effor_Bands_3.txt`
  -> `40_supporting_reference/support_matrices/31_support_matrices/Effor_Bands_3.txt`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/RDP v1 convergence implementation plan_2.txt`
  -> `40_supporting_reference/support_matrices/31_support_matrices/RDP_v1_convergence_implementation_plan_2.txt`
- `planning/v1/rdp_v1_execution_pack_2026-03-11/the_real_implmentation_plan_1.txt`
  -> `40_supporting_reference/support_matrices/31_support_matrices/the_real_implmentation_plan_1.txt`
- `planning/v1/rdp_v1_method_families_and_feature_matrix_2026-03-10.xlsx`
  -> `40_supporting_reference/support_matrices/31_support_matrices/rdp_v1_method_families_and_feature_matrix_2026-03-10.xlsx`
- `planning/old/workgin/merge_integration_plan_local_vs_network_2026-03-08.md`
  -> `40_supporting_reference/integration_history/38_integration_history/merge_integration_plan_local_vs_network_2026-03-08.md`
- `planning/old/workgin/merge_issue_log_2026-03-08.md`
  -> `40_supporting_reference/integration_history/38_integration_history/merge_issue_log_2026-03-08.md`
- `planning/old/scorign_refactor_plan.txt`
  -> `40_supporting_reference/scoring_and_assets_history/39_scoring_and_assets_history/scoring_refactor_plan_legacy_reference.txt`
- `planning/old/data_refactor_plan_assets_migration_draft.txt`
  -> `40_supporting_reference/scoring_and_assets_history/39_scoring_and_assets_history/data_refactor_plan_assets_migration_draft_legacy_reference.txt`

These absorbed support duplicates have now been retired from the old
`planning/v1/` surface, and the old `planning/old/workgin/` copies are now
retired as well.

### Absorbed into archive or legacy homes

- `planning/old/v1OLD/audit1/`
  -> `planning/archive/forensic_audit_2026/`
- `planning/old/v1OLD/bughunt/`
  -> `planning/archive/forensic_audit_2026/source_pack/v1OLD_bughunt/`
- old active-index residue
  -> `planning/legacy/v1_old_active_index/`
- `planning/v1/rdp_refactor_planning.zip`
  -> `planning/archive/rdp_v1_review_pass_bundle_20260309/source_pack/rdp_refactor_planning.zip`
- `planning/review/merge_issue_log_2026-03-08.md`
  -> `planning/archive/rdp_v1_review_pass_bundle_20260309/source_pack/merge_issue_log_2026-03-08.md`

These old raw-source copies have now been retired from the old top-level tree.
The old `v1OLD` forensic bundle itself is now retired as a source surface too.
The duplicate root `planning/old/v1OLD/bug_hunt.txt` prompt is now retired as
well because the preserved forensic archive already owns that file.

## Live backlink replacements made in this pass

Old private-workflow placeholders are now treated as replaced by:
- `planning/working/CURRENT_PHASE.md`
  -> `20_active_plans/CURRENT_PHASE_v1_2026-03-11.md`
- `planning/working/ACTIVE_TODO.md`
  -> `20_active_plans/ACTIVE_TODO_v0_2.md`
- `planning/working/CURRENT_RISKS.md`
  -> `20_active_plans/CURRENT_RISKS_v1_2026-03-11.md`
- `planning/review/findings_register.csv`
  -> `40_supporting_reference/support_matrices/31_support_matrices/findings_register.csv`
- `planning/review/support_matrix_test_map.md`
  -> `40_supporting_reference/support_matrices/31_support_matrices/support-to-test_map_7.txt`
- `planning/review/collated_programme.md`
  -> superseded by:
    - `00_CURRENT_STATE.md`
    - `01_WORKSTREAM_INDEX.md`
    - `04_ACTIVE_RUNBOOK.md`

## Remaining orphan or unclear files

None in the old top-level `rdp_v1` source surface.

The last preserved workbook copy was hash-checked against:
- `40_supporting_reference/support_matrices/31_support_matrices/rdp_v1_method_families_and_feature_matrix_2026-03-10.xlsx`

It has now been retired from `planning/v1/`.

Recently resolved legacy residues:
- `planning/v1/RDP governance charter.txt`
  - preserved as `40_supporting_reference/maintainer_notes/37_maintainer_reference/RDP_governance_charter_draft2_legacy_reference.txt`
  - retired from the old `planning/v1/` root
- `planning/v1/rdp_v1_execution_pack_2026-03-11/ACTIVE_TODO_starter_v1_2026-03-11.md`
  - preserved as `40_supporting_reference/maintainer_notes/37_maintainer_reference/ACTIVE_TODO_starter_v1_2026-03-11_legacy_reference.md`
  - retired from the old execution-pack surface

## Current judgement

`rdp_v1` is now safe to use without old-path fallback.

The old `planning/v1/` entry habit is retired.
What remains is ordinary support-layer discipline, not source-surface migration.
