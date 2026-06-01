# Stage35 Rank6 Local-Rescue Canary Design - 2026-04-30

Status: design only. Runtime is not launched by this note.

## Purpose

Test the softened rank-6 local-rescue policy shape without opening another broad
runtime batch.

Candidate rule:

- candidate rank is `6`
- and either:
  - `selected_start_match_ratio >= 0.437`
  - or `shallow_resume_minus_selected >= 0.400`

The rule is still a posthoc hypothesis. The canary should test implementation
discipline and no-regression behavior on deliberately chosen cells, not promote
the rule to production.

## Prediction Ledger

These predictions are for calibration/comparison, not blame assignment.

- real late local-rescue phenomenon:
  - `75-85%`
- narrow rank/slice policy improves selected cases:
  - `50-65%`
- general production policy from current signal:
  - `25-40%`
- exact `0.437` threshold survives as-is:
  - `15-25%`

When this analysis branch closes, explicitly compare the final outcome against
this ledger in chat.

## Source Evidence

- policy sketch:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_local_rescue_policy_sketch_2026-04-30.md`
- shallow-plus-deepening join:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/`
- selected-start safety output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T014439Z__stage35_rank6_selected_start_gate_safety_v1/`

## Proposed Canary Cells

### Cell A - hard-gate keep

- fixture/search:
  - `1511/search7004`
- candidate rank:
  - `6`
- candidate hash:
  - `51b7dab086e94186`
- selected-start:
  - `0.439`
- shallow resume:
  - `0.568`
- shallow minus selected:
  - `+0.129`
- deep resume:
  - `0.578`
- deep minus shallow:
  - `+0.010`
- reason:
  - tests the selected-start clause near threshold without relying on the
    shallow-delta clause

### Cell B - shallow-delta keep

- fixture/search:
  - `1111/search7002`
- candidate rank:
  - `6`
- candidate hash:
  - `74dfe3cb559629f7`
- selected-start:
  - `0.291`
- shallow resume:
  - `0.741`
- shallow minus selected:
  - `+0.450`
- deep resume:
  - `0.756`
- deep minus shallow:
  - `+0.015`
- reason:
  - tests the shallow-delta clause and recovers the largest positive rejected
    by the hard selected-start gate

### Cell C - observed-regression reject

- fixture/search:
  - `1111/search7004`
- candidate rank:
  - `6`
- candidate hash:
  - `511a29668b8c44d1`
- selected-start:
  - `0.320`
- shallow resume:
  - `0.433`
- shallow minus selected:
  - `+0.113`
- deep resume:
  - `0.426`
- deep minus shallow:
  - `-0.007`
- reason:
  - verifies that the policy rejects a known deepening regression

### Cell D - rejected-positive audit/control

- fixture/search:
  - `1411/search7005`
- candidate rank:
  - `6`
- candidate hash:
  - `b47e22bc63e7c189`
- selected-start:
  - `0.207`
- shallow resume:
  - `0.412`
- shallow minus selected:
  - `+0.205`
- deep resume:
  - `0.425`
- deep minus shallow:
  - `+0.013`
- reason:
  - measures known opportunity cost from the softened policy; this is not a
    policy failure by itself unless the branch goal becomes recall rather than
    no-regression safety

## Runtime Budget If Approved Later

Do not launch without explicit approval.

If approved, use a one-script, four-cell micro-canary with hardcoded constants:

- intended wallclock budget:
  - `45m`
- hard cap:
  - `2700s`
- per-cell rescue cap:
  - `600s`
- expected runtime basis:
  - prior deepening cells ran between about `75s` and `271s`
  - these four cells are already proven loadable from the deepening harvest
- stop condition:
  - stop after all four cells
  - stop if wallclock reaches `2700s`
  - after first executed rescue cell, stop if projected runtime exceeds `2700s`
- partial writeback:
  - after every cell
- progress:
  - completed-versus-total, elapsed, per-cell elapsed, and ETA after every cell

## Execution Semantics If Approved Later

- Cells A and B:
  - policy decision should be `keep`
  - run the same bounded deep Stage 3.5 continuation shape used by the completed
    deepening harvest
- Cell C:
  - policy decision should be `reject`
  - do not spend deep rescue runtime in policy mode
  - write a skip/audit row that records the known prior deepening regression
- Cell D:
  - policy decision should be `reject`
  - optional audit mode may replay or reference the prior deepening result, but
    it must be reported as opportunity-cost audit, not policy success

## Success Criteria

Implementation pass:

- all four cells load from repo-relative paths
- policy decisions match the expected keep/reject labels
- skipped cells are reported explicitly rather than silently omitted
- partial outputs are extractable after each cell

Science pass:

- Cell A and Cell B both remain nonnegative versus their shallow result
- Cell C is rejected by policy
- Cell D is reported as rejected-positive opportunity cost

Hold / fail:

- either keep cell regresses versus shallow
- Cell C is kept by the policy
- runtime exceeds the projected budget after first-cell projection
- output cannot distinguish policy skips from runtime failures

## Current Recommendation

Do not launch yet. The next implementation step, if approved, is a tiny
hardcoded canary runner that executes exactly this four-cell design and writes a
policy-decision row for every cell.
