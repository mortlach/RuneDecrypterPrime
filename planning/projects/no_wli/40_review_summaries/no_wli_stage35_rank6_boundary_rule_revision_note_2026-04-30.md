# Stage35 Rank6 Boundary Rule Revision Note - 2026-04-30

Status: offline revision note. No runtime authorized.

## Source Evidence

- recall/audit output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T021919Z__stage35_rank6_local_rescue_recall_audit_v1/`
- boundary-feature audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T032952Z__stage35_rank6_boundary_feature_audit_v1/`

## Question

What boundary features separate the three rejected positives from the two
rejected regressions without simply widening the policy?

## Boundary Rows

Rejected positives:

- `1411/search7005 rank 6 b47e22bc63e7c189`
  - audit minus shallow: `+0.013`
- `611/search7003 rank 6 826e5c871f444486`
  - audit minus shallow: `+0.011`
- `1411/search7004 rank 6 2632e79517bf1c7c`
  - audit minus shallow: `+0.005`

Rejected regressions:

- `1411/search7001 rank 6 c7d123cf849533ee`
  - audit minus shallow: `-0.002`
- `1111/search7004 rank 6 511a29668b8c44d1`
  - audit minus shallow: `-0.007`

## Feature Audit Result

- numeric features scanned:
  - `27`
- threshold sketches scanned:
  - `172`
- perfect one-feature separators:
  - `0`

Best zero-false-positive sketches:

- `audit_minus_retained >= 0.0045`
  - true positives `2`
  - false positives `0`
  - false negatives `1`
- `retained_best_match_ratio <= 0.4225`
  - true positives `2`
  - false positives `0`
  - false negatives `1`
- `selected_start_match_ratio <= 0.294`
  - true positives `2`
  - false positives `0`
  - false negatives `1`
- `shallow_resume_best_match_ratio <= 0.4225`
  - true positives `2`
  - false positives `0`
  - false negatives `1`

## Interpretation

- the boundary is not separable by the current simple numeric features
- the softened policy is safe but leaves real recall/opportunity cost
- simply widening the rule is not justified because it would admit known
  regressions
- the exact `0.437` selected-start threshold is not the right final mechanism

## Prediction Ledger Checkpoint

These were comparison/calibration predictions, not blame assignments.

- real late local-rescue phenomenon:
  - prediction `75-85%`
  - current read: supported
- narrow rank/slice policy improves selected cases:
  - prediction `50-65%`
  - current read: partially supported, but current rule is too conservative
- general production policy from current signal:
  - prediction `25-40%`
  - current read: not supported
- exact `0.437` threshold survives as-is:
  - prediction `15-25%`
  - current read: not supported

## Current Decision

- do not launch more runtime on this branch now
- do not promote the softened rule
- keep the local-rescue mechanism as real but still policy-incomplete

## Recommended Next

The next useful work is not another Stage 3.5 runtime batch. It is an offline
feature expansion that adds a different feature family, likely from route
composition or family/lineage context, then reruns the boundary audit. If that
still fails to separate the boundary, close this rank-6 policy line as a
mechanism insight rather than a policy candidate.

## Route-Lineage Follow-Up

The route-lineage follow-up is now complete:

- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T033637Z__stage35_rank6_route_lineage_boundary_audit_v1/`
- review note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_boundary_review_note_2026-04-30.md`

Result:

- single-feature perfect separators:
  - `0`
- two-feature perfect separators:
  - `141`
- most interpretable separator family:
  - candidate source rank `1`
  - high route novelty, for example
    `candidate_novelty_distance_to_anchor >= 173.5`

Updated recommendation:

- wait for external review
- do not promote or launch runtime from the route-lineage separator alone
- if the mechanism survives review, write a tiny held-out/disagreement
  confirmation design before any runtime
