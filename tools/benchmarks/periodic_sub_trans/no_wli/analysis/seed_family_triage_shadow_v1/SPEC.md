# Seed Family Triage Shadow v1

Authoritative contract:
- `planning/no_wli/30_analysis_specs/no_wli_seed_family_triage_shadow_v1_spec_2026-04-08.md`

This branch is a frozen-input, offline-only shadow triage and budget-allocation study.

Frozen inputs:
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T142942Z__score_stop_shadow_v2`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/20260408T154637Z__late_family_quality_v2`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/20260408T162219Z__late_family_quality_v3`

Outputs:
- `seed_triage_rows.jsonl`
- `family_priority_rows.jsonl`
- `budget_recommendation_rows.jsonl`
- `triage_summary.json`
- `triage_cases.md`

Non-goals:
- no live solver mutation
- no stop-policy promotion
- no seed-set widening
- no family reclustering
