# Stage35 Rank6 Route-Lineage Boundary Review Note - 2026-04-30

Status: external-review candidate note. No runtime authorized.

## Source Evidence

- recall/audit output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T021919Z__stage35_rank6_local_rescue_recall_audit_v1/`
- simple boundary-feature audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T032952Z__stage35_rank6_boundary_feature_audit_v1/`
- route-lineage boundary audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T033637Z__stage35_rank6_route_lineage_boundary_audit_v1/`

## Question

Can pre-runtime route-composition or lineage features separate the three
rejected rank-6 positives from the two rejected rank-6 regressions?

## Result

- rows:
  - `5`
- positives:
  - `3`
- regressions:
  - `2`
- numeric route-lineage features:
  - `27`
- categorical route-lineage features:
  - `5`
- single-feature perfect separators:
  - `0`
- two-feature perfect separators:
  - `141`

Most interpretable separator family:

- candidate is from Phase-C `phaseA_selected` source rank `1`
- and candidate is sufficiently far from the existing route:
  - `candidate_novelty_distance_to_anchor >= 173.5`
  - equivalent sketches also appear using distance to Phase-C anchor,
    Stage-3 top-k, or final-best key

Concrete kept rows under the preferred sketch:

- `1411/search7005 rank 6 b47e22bc63e7c189`
- `611/search7003 rank 6 826e5c871f444486`
- `1411/search7004 rank 6 2632e79517bf1c7c`

Rejected rows:

- `1411/search7001 rank 6 c7d123cf849533ee`
- `1111/search7004 rank 6 511a29668b8c44d1`

## Interpretation

- the prior simple numeric audit failed because it did not include route
  context
- the new separator is mechanistically plausible:
  - rank-6 local rescue appears to help when the rejected candidate is an
    early Phase-A-selected route that remains far from the Phase-C anchor or
    final-best route
  - the mild regression is too close to the existing route
  - the strong regression is far, but not source-rank `1`
- the separator is still posthoc on only five boundary rows
- the line is not ready for policy promotion or broad runtime

## External Review Questions

- Is `phaseA_selected source_rank == 1` a stable, intended lineage field here,
  or is it an incidental label from the candidate-pool writer?
- Is high novelty distance to the Phase-C anchor a defensible pre-runtime
  signal for local-rescue opportunity, or is it likely to overfit this
  boundary set?
- Should equivalent distance sketches use the Phase-C anchor, Stage-3 top-k
  minimum, or final-best key as the canonical feature?
- Is there an already-retained larger rank-6 set where these same pre-runtime
  features can be checked without launching new Stage 3.5 runtime?

## Current Decision

- wait for external review before launching more runtime
- do not promote the softened rank-6 rule
- do not promote the route-lineage separator
- keep the route-lineage separator as the next review hypothesis

## Recommended Next

If external review says the lineage fields are stable and the mechanism is
coherent, write a tiny confirmation design before runtime. The design should
target held-out rank-6 rows where the route-lineage rule and the prior
selected-start/shallow-delta rule disagree. If no held-out rows exist, close
the rank-6 policy line as a mechanism insight rather than a production
candidate.
