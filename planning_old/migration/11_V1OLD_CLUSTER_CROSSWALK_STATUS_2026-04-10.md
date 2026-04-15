# v1OLD cluster crosswalk status - 2026-04-10

This note records the current classification state of `planning/old/v1OLD/`.

The goal is not to rescue every old `v1OLD` note into a live home.
The goal is to:
- retire the bundles already preserved inside the new planning system
- keep only the genuinely unresolved residue visible

## Retired in this pass

### A. Forensic-audit bundle

Old source cluster:
- `planning/old/v1OLD/audit1/`
- `planning/old/v1OLD/bughunt/`
- `planning/old/v1OLD/audit_solver_blockers_2026-01-27.md`
- `planning/old/v1OLD/RuneDecrypterPrime Codebase Forensic Audit.pdf`

Preserved in the new system:
- `planning/archive/forensic_audit_2026/`
- `planning/archive/forensic_audit_2026/source_pack/`
- `planning/archive/forensic_audit_2026/source_pack/v1OLD_bughunt/`

Status:
- old copies retired

### B. Benchmark reference bundle

Old source cluster:
- `planning/old/v1OLD/rdp_community_benchmark_v1_1_spec/`
- `planning/old/v1OLD/bench_campaign_check/`

Preserved in the new system:
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/reference_packs/35_reference_packs/community_benchmark_v1_1_spec_bundle/`
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/reference_packs/35_reference_packs/community_readiness_reviews/`

Status:
- old copies retired

### C. Duplicate benchmark wrapper pack

Old source cluster:
- `planning/old/v1OLD/v1 benhcmar/`

Reason safe to retire:
- top-level benchmark docs were already absorbed into the benchmark home or archive
- the nested benchmark-spec bundle is already preserved in the benchmark reference pack
- the wrapper `README.md` is only generic planning-surface residue

Status:
- old duplicate wrapper pack retired

### D. Legacy col-then-sub reference cluster

Old source cluster:
- `planning/old/v1OLD/README.txt`
- `planning/old/v1OLD/tools/benchmarks/seed_utils_periodic_columnar_col_then_sub.py`
- `planning/old/v1OLD/tools/benchmarks/bench_solve_periodic_columnar_pipeline_col_then_sub.py`
- `planning/old/v1OLD/tests/utils/test_seed_utils_periodic_columnar_col_then_sub_bench.py`

Preserved in the new system:
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/legacy_seed_and_solve/37_legacy_seed_and_solve_reference/`

Status:
- old copies retired

## Still unresolved after this pass

These items remain in `planning/old/v1OLD/` and still need explicit judgement:

- `add_cribs_2/`
- `seed_gen_plans`
- `finster_iteration_plan_2026-02-17.md`
- `no_wli_pipeline_design_review_plan.md`

## Retired in the follow-on partial wave

### E. Forensic duplicate prompt

Old source file:
- `planning/old/v1OLD/bug_hunt.txt`

Preserved in the new system:
- `planning/archive/forensic_audit_2026/source_pack/bug_hunt.txt`

Status:
- old duplicate retired

### F. Scoring/Torch support duplicates

Old source files:
- `planning/old/v1OLD/README_TESTS_SCORING_2.md`
- `planning/old/v1OLD/scoring_contract_ecdf_abi.md`

Preserved in the new system:
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/README_TESTS_SCORING_2.md`
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/scoring_contract_ecdf_abi.md`

Status:
- old duplicates retired

## Retired in the final `v1OLD` closeout wave

### G. Hard-crib future-method note

Old source file:
- `planning/old/v1OLD/add_cribs_2/add cribs to RDP.md`

Preserved in the new system:
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/future_method_and_architecture/36_future_method_ideas/add_cribs_to_RDP_legacy_reference.md`

Status:
- old source retired

### H. No-WLI pipeline review note

Old source file:
- `planning/old/v1OLD/no_wli_pipeline_design_review_plan.md`

Preserved in the new system:
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/future_method_and_architecture/36_future_method_ideas/no_wli_pipeline_design_review_plan_legacy_reference.md`
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/future_method_and_architecture/36_future_method_ideas/NO_WLI_PIPELINE_DESIGN_REVIEW_REFERENCE_2026-04-10.md`

Status:
- old source retired

### I. Seed-generator design note

Old source file:
- `planning/old/v1OLD/seed_gen_plans`

Preserved in the new system:
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/legacy_seed_and_solve/37_legacy_seed_and_solve_reference/seed_gen_plans_legacy_reference.txt`
- `planning/projects/benchmark_campaign_v1_1/40_supporting_reference/legacy_seed_and_solve/37_legacy_seed_and_solve_reference/PERIODIC_COLUMNAR_KEY_GENERATOR_REFERENCE_2026-04-10.md`

Status:
- old source retired

### J. Finster solver research note

Old source file:
- `planning/old/v1OLD/finster_iteration_plan_2026-02-17.md`

Preserved in the new system:
- `planning/archive/finster_solver_research_20260217/source_pack/finster_iteration_plan_2026-02-17.md`
- `planning/archive/finster_solver_research_20260217/00_SUMMARY.md`
- `planning/archive/finster_solver_research_20260217/01_DOCUMENT_MAP.md`

Status:
- old source retired

## Current state after full `v1OLD` closeout

`planning/old/v1OLD/` no longer contains unresolved planning residue.

## Working rule

After this pass:
- do not use retired `v1OLD` bundles as reading surfaces
- use the new project/archive homes for the preserved material
- treat the remaining loose-root items as the next selective triage target
