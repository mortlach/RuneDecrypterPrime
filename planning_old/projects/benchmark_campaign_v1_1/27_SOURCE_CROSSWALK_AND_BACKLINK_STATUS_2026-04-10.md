# Benchmark campaign source crosswalk and backlink status - 2026-04-10

Status: active
Work status: in_progress
Project: benchmark_campaign_v1_1

## Purpose

This note records:
- which old benchmark-planning source packs fed this home
- which old files are now promoted into the new home
- which old files are absorbed, legacy-only, or still need explicit retirement
- whether live docs still depend on old `planning/` paths

## Main old source packs

Primary source surfaces:
- `planning/drafts/`
- `planning/old/v1OLD/rdp_community_benchmark_v1_1_spec/`
- `planning/old/v1OLD/bench_campaign_check/`
- selected old benchmark/refactor notes under `planning/old/`

## Promoted or absorbed into this home

### Front-door / contract / active-plan layer
- `planning/drafts/community_benchmark_unified_plan_v1_1.md`
  -> `20_active_plans/community_benchmark_unified_plan_v1_1.md`
- `planning/drafts/campaign_spec_v1_1.md`
  -> `10_contracts/campaign_spec_v1_1.md`
- `planning/drafts/setup_and_preflight_v1_1_spec.md`
  -> `30_validation_and_setup/setup_and_preflight_v1_1_spec.md`
- `planning/drafts/scoring_paths_torch_compliance_v1_plan.md`
  -> `20_active_plans/scoring_paths_torch_compliance_v1_plan.md`

### Supporting reference promoted into this home
- `planning/drafts/BENCH_CAMPAIGN_CLEANUP_PLAN_2026-02-25.md`
  -> `40_supporting_reference/runner_cleanup_and_refactor/34_runner_cleanup_and_refactor_history/BENCH_CAMPAIGN_CLEANUP_PLAN_2026-02-25.md`
- `planning/drafts/benchmarks_periodic_sub_trans_refactor_plan.md`
  -> `40_supporting_reference/runner_cleanup_and_refactor/34_runner_cleanup_and_refactor_history/benchmarks_periodic_sub_trans_refactor_plan.md`
- `planning/drafts/no_wli_stage3_torch_avg_fulltext_crash_report_2026-02-23.md`
  -> `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/no_wli_stage3_torch_avg_fulltext_crash_report_2026-02-23.md`
- `planning/drafts/v1_outward_bugs_bloat_docs_log_2026-02-23.md`
  -> `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/v1_outward_bugs_bloat_docs_log_2026-02-23.md`
- `planning/drafts/torch_scoring_pipeline_upgrade_plan_v1.md`
  -> `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/torch_scoring_pipeline_upgrade_plan_v1.md`
- `planning/drafts/fully_torch_compliant_notes.txt`
  -> `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/fully_torch_compliant_notes.txt`
- `planning/drafts/scoring_speed_investigation_2026-02-22.md`
  -> `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/scoring_speed_investigation_2026-02-22.md`
- `planning/old/v1OLD/rdp_community_benchmark_v1_1_spec/`
  -> `40_supporting_reference/reference_packs/35_reference_packs/community_benchmark_v1_1_spec_bundle/`
- `planning/old/v1OLD/bench_campaign_check/COMMUNITY_CAMPAIGN_READINESS_REVIEW_2026-02-22.md`
  -> `40_supporting_reference/reference_packs/35_reference_packs/community_readiness_reviews/COMMUNITY_CAMPAIGN_READINESS_REVIEW_2026-02-22.md`
- `planning/old/v1OLD/v1 benhcmar/`
  -> duplicate wrapper pack; substantive files were already absorbed into the
     live benchmark home, support layers, and archive homes
- `planning/old/v1OLD/add_cribs_2/add cribs to RDP.md`
  -> `40_supporting_reference/future_method_and_architecture/36_future_method_ideas/add_cribs_to_RDP_legacy_reference.md`
- `planning/old/nowli_imrpovements_refactor_for_benchcamp.txt`
  -> `40_supporting_reference/future_method_and_architecture/36_future_method_ideas/nowli_improvements_refactor_for_benchcamp_legacy_reference.txt`
- `planning/old/nowli_imrpovements_refactor_for_benchcamp_review.txt`
  -> `40_supporting_reference/future_method_and_architecture/36_future_method_ideas/nowli_improvements_refactor_for_benchcamp_review_legacy_reference.txt`
- `planning/old/phased_plan.txt`
  -> `40_supporting_reference/future_method_and_architecture/36_future_method_ideas/PHASED_RUNNER_STAGE_ENGINE_ROADMAP_REFERENCE_2026-04-09.md`
- `planning/old/v1OLD/no_wli_pipeline_design_review_plan.md`
  -> `40_supporting_reference/future_method_and_architecture/36_future_method_ideas/no_wli_pipeline_design_review_plan_legacy_reference.md`
- `planning/old/v1OLD/README_TESTS_SCORING_2.md`
  -> `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/README_TESTS_SCORING_2.md`
- `planning/old/v1OLD/scoring_contract_ecdf_abi.md`
  -> `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/scoring_contract_ecdf_abi.md`
- `planning/old/v1OLD/seed_gen_plans`
  -> `40_supporting_reference/legacy_seed_and_solve/37_legacy_seed_and_solve_reference/seed_gen_plans_legacy_reference.txt`

### Absorbed by newer front-door docs
- `planning/drafts/v1_docset_map.md`
  -> absorbed by `03_DOCUMENT_MAP.md`
- `planning/drafts/todo list`
  -> absorbed by `20_active_plans/ACTIVE_TODO_v0_4.md`

The absorbed benchmark duplicate set above has now been retired from the old
`planning/drafts/` surface.
The old future-architecture root copies in `planning/old/` are now also retired.
The old `v1OLD` benchmark reference and duplicate-wrapper copies are now retired
as well.
The old `v1OLD` scoring/Torch duplicate notes are now retired as well.
The old `v1OLD` future-method and legacy-seed notes are now retired as well.

## Not promoted into this home

### Deliberately outside this project's live/support boundary
- `planning/drafts/score_harden_v2.txt`
  - better treated as no-WLI stop-study residue than benchmark-home truth
- `planning/drafts/v1_core_bugs_bloat_docs_log_2026-02-23.md`
  - better treated as repo-level / `rdp_v1` audit context than benchmark-home truth

### Legacy or obsolete residue
- `planning/drafts/README.md`
  - obsolete local/gitignored-era note; retired from the old drafts surface

## Live backlink status

Active/front-door docs should now read within this home:
- `00_CURRENT_STATE.md`
- `03_DOCUMENT_MAP.md`
- `04_ACTIVE_RUNBOOK.md`
- `20_active_plans/community_benchmark_unified_plan_v1_1.md`
- `20_active_plans/scoring_paths_torch_compliance_v1_plan.md`
- `30_validation_and_setup/benchmark_campaign_current_code_crosscheck_note.md`
- `30_validation_and_setup/benchmark_campaign_crosscheck_round2_2026-04-09.md`

Supporting references may still mention old source paths as historical provenance.
That is acceptable as long as those references do not function as the live reading
surface.

## Current judgement

The benchmark home is now slightly past the phase `rdp_v1` first reached after
its first closeout pass:
- the content migration is mostly done
- the main absorbed benchmark duplicates in `planning/drafts/` are retired
- the remaining issue is no longer intake
- the remaining issue is the two leftover non-benchmark draft files plus the
  broader old-cluster cleanup
