# Stage35 Rank6 Route-Lineage Review Action Note - 2026-04-30

Status: review action completed. No runtime launched.

## Review Source

The dev-facing review draft was moved from the repository root to:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_final_dev_review_draft_2026-04-30.md`

Review verdict:

- score-improvement direction:
  - strong enough to continue
- mechanism:
  - credible source-rank plus anchor-novelty hypothesis
- policy readiness:
  - no
- runtime readiness:
  - no
- next step:
  - strict offline held-out / disagreement scan using pre-runtime-safe lineage
    fields

## Action Taken

Implemented strict offline confirmation-prep extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_route_lineage_confirmation_prep_v1.py`

Added dedicated tests:

- `tests/tools/test_no_wli_stage35_rank6_route_lineage_confirmation_prep_v1.py`

The extractor classifies retained rank-6 rows using only the action-safe
route-lineage rule:

- `candidate_source == "phaseA_selected"`
- `candidate_source_rank == 1`
- `candidate_novelty_distance_to_anchor >= 173.5`

It explicitly does not use posthoc/final fields as action-rule inputs.

Missing lineage is classified as:

- `E_invalid_missing_lineage`

not as a negative/reject decision.

## Output

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T151237Z__stage35_rank6_route_lineage_confirmation_prep_v1/`

Files:

- `stage35_rank6_route_lineage_confirmation_prep_rows.csv`
- `stage35_rank6_route_lineage_confirmation_prep_summary.json`
- `stage35_rank6_route_lineage_confirmation_prep_readout.md`

## Result

- valid rows:
  - `21`
- invalid rows:
  - `1`
- invalid reason:
  - `missing_candidate_novelty_distance_to_anchor`: `1`
- old softened keep/reject:
  - `10 / 12`
- route-lineage keep/reject:
  - `9 / 12`
- rule disagreements:
  - `9`

Group counts:

- A old reject / route keep:
  - `4`
- B old keep / route reject:
  - `5`
- C both keep:
  - `5`
- D both reject:
  - `7`
- E invalid:
  - `1`

Group A rows:

- `611/search7003 826e5c871f444486`
- `1111/search7001 d94845511e181f7c`
- `1411/search7004 2632e79517bf1c7c`
- `1411/search7005 b47e22bc63e7c189`

Group B rows:

- `611/search7005 90f50f7318f07b92`
- `1111/search7002 0b10860e7856594e`
- `1511/search7002 6c150760d647fc3d`
- `1511/search7003 35a24c408eb88e7a`
- `1511/search7004 51b7dab086e94186`

## Verification

- `py -3 -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_route_lineage_confirmation_prep_v1.py`
- `py -3 -m pytest tests/tools/test_no_wli_stage35_rank6_route_lineage_confirmation_prep_v1.py`
  - `9 passed`

## Interpretation

The review was correct: the route-lineage mechanism is credible enough to keep
moving, but the line needed a stricter offline confirmation-prep step before
any runtime.

The confirmation-prep scan found both:

- predicted recovered-positive candidates where the old rule rejected and the
  route-lineage rule keeps
- safety-check candidates where the old rule kept and the route-lineage rule
  rejects

That means an honest tiny confirmation design surface exists, but it still
requires a separate written design and budget before runtime.

## Recommended Next

Inspect Group A and Group B against existing shallow/deep evidence, then write
a fixed-rule tiny confirmation design. Do not launch it until the design names
the rows, expected value, runtime budget, and stop condition.
