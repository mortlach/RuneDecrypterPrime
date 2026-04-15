# Old surface retirement matrix - 2026-04-10

This file records how the old top-level planning surfaces should be treated now
that the active homes have had their first migration-closeout passes.

## Goal

Use one planning system for everyday work:
- the control layer under `planning/`
- the active homes under `planning/projects/`

Treat older top-level planning surfaces as:
- explicit upstream exceptions
- deprecated stubs
- classified retirement residue

Do not delete anything just because a new home exists.
Delete or quarantine old surfaces only when:
- live backlinks are replaced
- the old surface no longer competes with the new home
- any preserved provenance/archive role is explicit

## Status labels

- `canonical_live`
  - this is part of the working planning system
- `upstream_exception`
  - intentionally still live outside the migrated bundle
- `keep_stub_only`
  - keep only as a redirect/deprecation surface
- `retire_after_link_cleanup`
  - content is absorbed, but old paths still need final retirement cleanup
- `retire_after_archive_or_support_confirmation`
  - content is absorbed, but the old copy should remain until archive/support
    preservation is clearly settled
- `mixed_cluster_needs_triage`
  - some items are absorbed, some are not yet cleanly classified
- `retire_now_safe`
  - safe to remove once ordinary repo hygiene/deletion timing is chosen
- `retired`
  - retirement has already been executed; the row remains only as history

## Matrix

| Old surface or cluster | Current role | Status | Primary destination / reason | Main blocker before retirement |
|---|---|---|---|---|
| `planning/` | new control layer + active homes | `canonical_live` | target system | none |
| `planning/no_wli/` | upstream no-WLI method-development home | `upstream_exception` | explicit upstream live home kept outside this migration focus; internal legacy residue was retired into `planning/legacy/no_wli_live_surface_residue_2026-04-14/` on 2026-04-14 | separate future decision on whether it stays external permanently |
| pre-promotion `planning/archive/` wrapper surface | old top-level archive wrapper | `retired` | preserved inside `planning/archive/no_wli_planning_refactor_20260404/95_evidence_snapshots/top_level_planning_archive_surface_20260404.zip`; canonical `planning/archive/` now belongs to the promoted root | none |
| `planning/drafts/` | old benchmark/no-WLI draft surface | `retired` | removed on 2026-04-10 after preserved items were rehomed or explicitly retired | none |
| `planning/working/` | deprecated staging area | `keep_stub_only` | already reduced to redirect README | keep only until no legacy writer still expects the path |
| `planning/review/` | old repo-level review surface | `retired` | emptied and removed on 2026-04-10 after archive/support preservation and duplicate cleanup | none |
| `planning/plna_refactor/` | retired wrapper around the formerly nested canonical bundle | `retired` | preserved in `planning/legacy/retired_root_wrappers/plna_refactor_root_wrapper_2026-04-10/` and removed after root promotion | none |
| `planning/v1/rdp_v1_execution_pack_2026-03-11/` | old `rdp_v1` execution pack | `retired` | absorbed files are retired; `ACTIVE_TODO_starter_v1_2026-03-11.md` is preserved in `projects/rdp_v1/40_supporting_reference/maintainer_notes/37_maintainer_reference/` | none |
| `planning/v1/` top-level `rdp_v1` governance/refactor/support docs | old repo-level active pack | `retired` | workbook and supporting duplicates are preserved inside `projects/rdp_v1/40_supporting_reference/`; the old root was removed on 2026-04-10 | none |
| `planning/v1/rdp_refactor_planning.zip` | raw `rdp_v1` review bundle | `retired` | preserved in `archive/rdp_v1_review_pass_bundle_20260309/` and removed from `planning/v1/` on 2026-04-10 | none |
| `planning/v1/rdp_v1_method_families_and_feature_matrix_2026-03-10.xlsx` | structured `rdp_v1` support workbook | `retired` | preserved in `projects/rdp_v1/40_supporting_reference/support_matrices/31_support_matrices/` and removed from the old root on 2026-04-10 after hash confirmation | none |
| `planning/drafts/` canonical benchmark docs (`community_benchmark_unified_plan_v1_1.md`, `campaign_spec_v1_1.md`, `setup_and_preflight_v1_1_spec.md`, `scoring_paths_torch_compliance_v1_plan.md`) | old live benchmark front door | `retired` | absorbed into `projects/benchmark_campaign_v1_1/` live pack and removed from `planning/drafts/` on 2026-04-10 | none |
| `planning/drafts/` benchmark support docs (`BENCH_CAMPAIGN_CLEANUP_PLAN_2026-02-25.md`, `benchmarks_periodic_sub_trans_refactor_plan.md`, `no_wli_stage3_torch_avg_fulltext_crash_report_2026-02-23.md`, `v1_outward_bugs_bloat_docs_log_2026-02-23.md`, Torch/scoring notes) | old benchmark support cluster | `retired` | absorbed into `projects/benchmark_campaign_v1_1/40_supporting_reference/` and removed from `planning/drafts/` on 2026-04-10 | none |
| `planning/drafts/v1_docset_map.md` and `planning/drafts/todo list` | older benchmark routing residue | `retired` | absorbed by `03_DOCUMENT_MAP.md` and `20_active_plans/ACTIVE_TODO_v0_4.md`, then removed from `planning/drafts/` on 2026-04-10 | none |
| `planning/drafts/README.md` | obsolete local/gitignored-era note | `retired` | removed in the first safe retirement wave on 2026-04-10 | none |
| `planning/drafts/lp_registry_review_bundle/` | old LP registry review source bundle | `retired` | absorbed into `completed/lp_domain/` review bundle and removed from `planning/drafts/` on 2026-04-10 | none |
| `planning/drafts/lp_registry_review_bundle.zip` | zipped duplicate of LP registry bundle | `retired` | preserved in `completed/lp_domain/95_evidence_snapshots/lp_registry_review_bundle.zip` and removed from `planning/drafts/` on 2026-04-10 | none |
| `planning/drafts/score_harden_v2.txt` | no-WLI/stop-study draft residue outside benchmark-home truth | `retired` | preserved in `archive/no_wli_stop_science_review_draft_20260408/` and removed from `planning/drafts/` on 2026-04-10 | none |
| `planning/drafts/v1_core_bugs_bloat_docs_log_2026-02-23.md` | repo-level bug/bloat draft residue outside benchmark-home truth | `retired` | preserved in `archive/forensic_audit_2026/source_pack/v1_core_bugs_bloat_docs_log_2026-02-23.md` and removed from `planning/drafts/` on 2026-04-10 | none |
| `planning/review/merge_issue_log_2026-03-08.md` | raw review note used by `rdp_v1` migration | `retired` | preserved in `archive/rdp_v1_review_pass_bundle_20260309/` and removed from `planning/review/` on 2026-04-10 | none |
| `planning/review/merge_review.txt` | duplicate-only review residue | `retired` | removed in the first safe retirement wave on 2026-04-10 | none |
| `planning/review/notes` | stray no-WLI merge follow-up note | `retired` | preserved in `archive/no_wli_merge_followup_20260308/` and removed from the old review surface on 2026-04-10 | none |
| `planning/old/v1OLD/rdp_community_benchmark_v1_1_spec/` | old benchmark reference bundle | `retired` | preserved under `projects/benchmark_campaign_v1_1/40_supporting_reference/reference_packs/35_reference_packs/community_benchmark_v1_1_spec_bundle/` | none |
| `planning/old/v1OLD/bench_campaign_check/` | old benchmark readiness/review cluster | `retired` | readiness review promoted into benchmark reference packs | none |
| `planning/old/v1OLD/v1 benhcmar/` | old duplicate benchmark wrapper pack | `retired` | substantive docs absorbed into benchmark support/archive homes; wrapper README is duplicate residue | none |
| `planning/old/v1OLD/README.txt`, `planning/old/v1OLD/tools/`, `planning/old/v1OLD/tests/` | old legacy col-then-sub reference cluster | `retired` | preserved in `projects/benchmark_campaign_v1_1/40_supporting_reference/legacy_seed_and_solve/37_legacy_seed_and_solve_reference/` | none |
| `planning/old/workgin/` | old merge/integration residue | `retired` | preserved in `projects/rdp_v1/40_supporting_reference/integration_history/`; the overlapping issue-log context is also preserved in `archive/phased_refactor_and_review/source_docs/` | none |
| `planning/old/` root LP-domain completion docs (`lp_domain_spec_v1.txt`, `lp_domain_implementation_plan_v1.txt`, `lp_registry_integration_review_20260307.txt`) | completed LP-domain source residue | `retired` | preserved in `completed/lp_domain/source_docs/` | none |
| `planning/old/` root phased/refactor docs (`external_reviewer_handoff_20260307.txt`, `phased_plan.txt`, `phased_plan_review.txt`, `phased_plan_execution_sync_20260306*.txt`, `scorign_refactor_plan.txt`, `data_refactor_plan_assets_migration_draft.txt`) | old phased/refactor source residue | `retired` | preserved in `archive/phased_refactor_and_review/` and `projects/rdp_v1/40_supporting_reference/scoring_and_assets_history/` | none |
| `planning/old/` root future-runner docs (`nowli_imrpovements_refactor_for_benchcamp.txt`, `nowli_imrpovements_refactor_for_benchcamp_review.txt`) | old future-architecture residue | `retired` | preserved in `projects/benchmark_campaign_v1_1/40_supporting_reference/future_method_and_architecture/36_future_method_ideas/` | none |
| `planning/old/` root working-set index residue (`ACTIVE_INDEX.txt`, `REMAINING_ITEMS_STATUS.txt`) | old no-WLI/phased working-set index residue | `retired` | preserved in `archive/phased_refactor_and_review/source_docs/` and `archive/no_wli_planning_refactor_20260404/source_pack/90_legacy_index/` | none |
| `planning/old/v1OLD/audit1/`, `planning/old/v1OLD/bughunt/`, top-level forensic note/pdf | old forensic-audit bundle | `retired` | preserved in `archive/forensic_audit_2026/` | none |
| `planning/old/v1OLD/add_cribs_2/` | old hard-crib future-method note | `retired` | preserved in `projects/benchmark_campaign_v1_1/40_supporting_reference/future_method_and_architecture/36_future_method_ideas/add_cribs_to_RDP_legacy_reference.md` | none |
| `planning/old/v1OLD/seed_gen_plans` | old periodic-columnar seed-generator design note | `retired` | preserved in `projects/benchmark_campaign_v1_1/40_supporting_reference/legacy_seed_and_solve/37_legacy_seed_and_solve_reference/seed_gen_plans_legacy_reference.txt` | none |
| `planning/old/v1OLD/bug_hunt.txt` | old forensic prompt duplicate | `retired` | preserved in `archive/forensic_audit_2026/source_pack/bug_hunt.txt` | none |
| `planning/old/v1OLD/README_TESTS_SCORING_2.md`, `planning/old/v1OLD/scoring_contract_ecdf_abi.md` | old scoring/Torch support duplicates | `retired` | preserved in `projects/benchmark_campaign_v1_1/40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/` | none |
| `planning/old/v1OLD/no_wli_pipeline_design_review_plan.md` | old no-WLI benchmark design review note | `retired` | preserved in `projects/benchmark_campaign_v1_1/40_supporting_reference/future_method_and_architecture/36_future_method_ideas/no_wli_pipeline_design_review_plan_legacy_reference.md` | none |
| `planning/old/v1OLD/finster_iteration_plan_2026-02-17.md` | old Finster solver research note | `retired` | preserved in `archive/finster_solver_research_20260217/` | none |
| `planning/old/v1OLD/` | old mixed legacy cluster | `retired` | retired after explicit crosswalk and preservation of the remaining loose-root items | none |
| `planning/old/working_archive_2026-04-02_stage35/` | old no-WLI stage35 transition archive cluster | `retired` | preserved in `archive/no_wli_stage35_transition_20260402/` and retired after full source-pack mirroring | none |
| `planning/old/no_wli_legacy_migration_2026-04-04/` | old no-WLI frozen migration and review/research bundle | `retired` | preserved through `archive/no_wli_planning_refactor_20260404/`, `archive/no_wli_external_review_passes_20260326_20260330/`, and `projects/p13_real_ciphertext_campaign/40_supporting_reference/reference_context/` | none |
| `planning/rdp_planning_bundle_v0_29_2026-04-09.zip` | loose top-level planning-bundle snapshot | `retired` | moved to `archive/planning_bundle_snapshot_20260409/95_evidence_snapshots/` on 2026-04-10 | none |

## Working rule now

For ordinary planning work:
1. start in `planning/`
2. use the relevant active home
3. only touch old top-level planning surfaces if:
   - a crosswalk note explicitly points there, or
   - the retirement matrix still marks the cluster unresolved

## First retirement wave executed

Executed on 2026-04-10:
- retired `planning/drafts/README.md`
- retired `planning/review/merge_review.txt`

Not retired after first audit:
- `planning/review/notes`
  - this was identified as a real no-WLI follow-up note rather than an empty
  leftover folder
  - it has now been preserved in `archive/no_wli_merge_followup_20260308/`

Second follow-on retirement executed on 2026-04-10:
- retired `planning/review/notes` after archive preservation

Third follow-on retirement executed on 2026-04-10:
- retired `planning/review/merge_issue_log_2026-03-08.md` after archive preservation
- retired `planning/v1/rdp_refactor_planning.zip` after archive preservation

Fourth follow-on retirement executed on 2026-04-10:
- retired `planning/drafts/lp_registry_review_bundle/` after completed-home absorption
- retired `planning/drafts/lp_registry_review_bundle.zip` after evidence-snapshot preservation

Fifth follow-on retirement executed on 2026-04-10:
- retired absorbed benchmark live/support duplicates from `planning/drafts/`
- retired absorbed benchmark routing residue (`v1_docset_map.md`, `todo list`)

Sixth follow-on retirement executed on 2026-04-10:
- retired the empty `planning/review/` surface after its contents were already removed or preserved

Seventh follow-on retirement executed on 2026-04-10:
- retired the absorbed `planning/v1/` live/support duplicate set
- left only the unresolved `ACTIVE_TODO` starter, one older governance draft,
  and the preserved workbook in place

Eighth follow-on retirement executed on 2026-04-10:
- preserved and retired `planning/v1/RDP governance charter.txt`
- preserved and retired `planning/v1/rdp_v1_execution_pack_2026-03-11/ACTIVE_TODO_starter_v1_2026-03-11.md`
- preserved and retired `planning/drafts/score_harden_v2.txt`
- preserved and retired `planning/drafts/v1_core_bugs_bloat_docs_log_2026-02-23.md`

Ninth follow-on retirement executed on 2026-04-10:
- retired the empty `planning/drafts/` surface
- retired the empty `planning/v1/rdp_v1_execution_pack_2026-03-11/` shell

Tenth follow-on retirement executed on 2026-04-10:
- retired `planning/old/workgin/` after support/archive preservation
- retired the old LP-domain root docs after completed-home preservation
- retired the old phased/refactor root docs after archive/support preservation
- retired the old future-runner root docs after benchmark support preservation
- retired the old working-set index residue after archive preservation

Eleventh follow-on retirement executed on 2026-04-10:
- retired the preserved `v1OLD` forensic bundle
- retired the preserved `v1OLD` benchmark reference bundle
- retired the duplicate `v1OLD/v1 benhcmar/` wrapper pack
- retired the preserved `v1OLD` legacy col-then-sub cluster

Twelfth follow-on retirement executed on 2026-04-10:
- retired the duplicate `v1OLD/bug_hunt.txt` forensic prompt
- retired the duplicate `v1OLD` scoring/Torch support notes

Thirteenth follow-on retirement executed on 2026-04-10:
- retired the last `v1OLD` specialist and loose-root notes after explicit preservation
- retired the `planning/old/v1OLD/` surface itself

Fourteenth follow-on retirement executed on 2026-04-10:
- completed the `archive/no_wli_stage35_transition_20260402/` source pack by
  mirroring `merge_integration_plan_local_vs_network_2026-03-08.md`
- retired `planning/old/working_archive_2026-04-02_stage35/`

Fifteenth follow-on retirement executed on 2026-04-10:
- preserved the two fuller frozen refactor-input packs under:
  `archive/no_wli_planning_refactor_20260404/95_evidence_snapshots/`
- preserved the two external-review packs under:
  `archive/no_wli_external_review_passes_20260326_20260330/95_evidence_snapshots/`
- retired `planning/old/no_wli_legacy_migration_2026-04-04/`

Sixteenth follow-on retirement executed on 2026-04-10:
- preserved the old pre-promotion `planning/archive/no_wli_planning_refactor_20260404/`
  surface as:
  `archive/no_wli_planning_refactor_20260404/95_evidence_snapshots/top_level_planning_archive_surface_20260404.zip`
- retired the old pre-promotion `planning/archive/` wrapper surface
- retired the last old `planning/v1/` workbook copy after hash confirmation
- retired the old top-level `planning/v1/` surface
- moved the loose top-level `planning/rdp_planning_bundle_v0_29_2026-04-09.zip`
  snapshot into `archive/planning_bundle_snapshot_20260409/95_evidence_snapshots/`

Seventeenth follow-on retirement executed on 2026-04-10:
- promoted the nested canonical bundle from `planning/plna_refactor/planning/`
  to the top-level `planning/` root
- preserved the retired `planning/plna_refactor/` wrapper under:
  `planning/legacy/retired_root_wrappers/plna_refactor_root_wrapper_2026-04-10/`
- retired the old `planning/plna_refactor/` wrapper

## Immediate next follow-up topics

Follow-up work is now structural maintenance, not old-surface retirement:
1. keep `planning/working/` as a compatibility stub only
2. keep `planning/no_wli/` explicit as the one upstream live exception
3. use `13_FINAL_CANONICAL_CUTOVER_DECISION_2026-04-10.md` as the repo-wide
   cut-over reference

Eighteenth follow-on retirement executed on 2026-04-14:
- retired the in-tree `planning/no_wli/90_legacy_index/` residue into
  `planning/legacy/no_wli_live_surface_residue_2026-04-14/source_docs/90_legacy_index/`
- retired the stray duplicate/spec-draft residue from
  `planning/no_wli/30_analysis_specs/` into
  `planning/legacy/no_wli_live_surface_residue_2026-04-14/source_docs/30_analysis_specs/`
- kept the active no-WLI live surface limited to the curated `00-04` layer plus
  `10/20/30/40/50/60`
