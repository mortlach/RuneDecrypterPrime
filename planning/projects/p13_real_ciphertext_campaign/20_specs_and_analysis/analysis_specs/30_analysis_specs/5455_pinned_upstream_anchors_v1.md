# 5455 pinned upstream anchors v1

Status: active
Work status: done
Project: p13_real_ciphertext_campaign

This note records the first pinned upstream anchors for the `5455` thread.

Routing notes:
- live upstream home route:
  - `planning/projects/no_wli/00_CURRENT_STATE.md`
  - `planning/projects/no_wli/04_ACTIVE_RUNBOOK.md`
- upstream usage rule:
  - `20_specs_and_analysis/analysis_specs/30_analysis_specs/no_wli_upstream_reference_policy.md`

## Canonical payload anchors

### A. Transcript/API source anchor
Use:
- LP pages 54â€“55
- section 13 route
- `load_lp_master_section(13, split="page")`

Reason:
- already verified in code/tests
- already tied to the `5455` planning brief

### B. Expected span-length anchor
Use:
- expected ciphertext-index length `308`

Reason:
- already asserted in transcript/API parity tests
- makes the control package concrete and checkable

## First pinned upstream evidence anchors

### C. Solve-proof support anchor
Use:
- `tools/benchmarks/solve_proof/README.md`
- `tools/benchmarks/solve_proof/README_pipeline.md`
- `tools/benchmarks/solve_proof/RUN_PLAN.md`
- `tools/benchmarks/solve_proof/solve_status_v1.json`

Reason:
- this is the clearest benchmark/control discipline surface already tied into
  the project home

### D. No-WLI project-state anchor
Use:
- `planning/projects/no_wli/00_CURRENT_STATE.md`
- `planning/projects/no_wli/01_EXPERIMENT_INDEX.md`
- `planning/projects/no_wli/04_ACTIVE_RUNBOOK.md`

Reason:
- these are the clearest upstream method-development truth files

### E. P13 readiness-context anchor
Use:
- `35_reference_context/p13_readiness_context/no_wli_solve_integrity_plan_2026-03-21.md`
- `35_reference_context/p13_readiness_context/capability_ladder_no_wli_periodic_sub_trans_2026-03-21.md`

Reason:
- these are broader readiness/context notes that explain why p13 is a meaningful
  harder frontier
- they should remain context only, not fake direct `5455` thread history

## Working rule

For the next result note, these should be treated as the first default upstream
anchors unless a later controlled reason replaces them.

