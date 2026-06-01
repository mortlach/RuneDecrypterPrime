# no-WLI Stage 3.5 Rank-6 Route-Lineage Review and Next-Step Draft

Date: 2026-04-30  
Status: dev-facing review draft  
Topic: Stage 3.5 rank-6 local-rescue route-lineage boundary

---

## 1. Purpose of this note

This note summarises the current review of the Stage 3.5 rank-6 local-rescue route-lineage work and gives a concrete next-step recommendation for development.

The goal is to keep the result moving forward without over-promoting it.

The main question is:

> Can the route-lineage signal explain which rank-6 Stage 3.5 local-rescue candidates are worth deepening, so that we recover missed positives without admitting the known regressions?

The current answer is:

> The signal is credible enough for strict offline confirmation-prep, but not yet ready for runtime or policy promotion.

---

## 2. Bottom-line verdict

```text
Score-improvement direction:
  strong enough to continue

Mechanism:
  credible source-rank + anchor-novelty hypothesis

Policy readiness:
  no

Runtime readiness:
  no

Next step:
  strict offline held-out / disagreement scan using pre-runtime-safe lineage fields
```

This is not a weak or failed result. It is a good mechanism signal that needs one more disciplined offline step before any runtime experiment.

---

## 3. Review inputs checked

The review was based on the actual uploaded review pack and paired source bundle.

Review pack:

```text
planning/projects/no_wli/40_review_summaries/
no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30/
```

Source bundle:

```text
output/tools/get_src_extended_review_bundle/
get_src_extended_review_bundle__20260430T041152Z.zip
```

Important review files checked:

```text
01_summary_for_reviewers.md
02_status_and_interpretation.md
06_evidence_ledger.md

20_result_readouts/01_selected_start_gate_safety_readout.md
20_result_readouts/02_rank6_local_rescue_canary_readout.md
20_result_readouts/04_rank6_local_rescue_recall_audit_readout.md
20_result_readouts/06_rank6_boundary_feature_audit_readout.md
20_result_readouts/07_route_lineage_boundary_audit_readout.md

30_manifests/07_rank6_local_rescue_recall_audit_rows.csv
30_manifests/11_route_lineage_boundary_audit_summary.json
30_manifests/12_route_lineage_boundary_feature_rows.csv
30_manifests/14_route_lineage_boundary_two_feature_scan_rows.csv
30_manifests/src_bundle_code_targets.csv
30_manifests/raw_output_bundle_locator.csv
```

Important source files checked:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/
  extract_stage35_rank6_route_lineage_boundary_audit_v1.py
  extract_stage35_rank6_boundary_feature_audit_v1.py
  run_stage35_rank6_local_rescue_canary_v1.py
  run_stage35_rank6_local_rescue_recall_audit_v1.py

tools/benchmarks/periodic_sub_trans/no_wli/
  stage3_two_phase.py
  stage35_substitution_solver.py
  artifact_resume.py

tests/tools/
  test_no_wli_stage3_phasec.py
  test_no_wli_stage35_substitution_solver.py
  test_no_wli_artifact_resume.py
```

No claim in this note should be read as a runtime approval.

---

## 4. Plain-English interpretation

The Stage 3.5 rank-6 local-rescue work is trying to answer this:

> Some rank-6 candidates become better after local rescue, but some get worse. Can we tell the difference before spending runtime?

The current evidence says:

```text
Yes, there is a real score-improvement region.

No, rank 6 alone is not safe.

The best current explanation is:
  keep rank-6 candidates that are early phaseA-selected routes
  and are far enough from the current Phase-C anchor.

But this needs strict offline confirmation before runtime.
```

The useful mechanism can be summarised as:

```text
Useful rank-6 Stage 3.5 rescue appears to require both:
  1. candidate source rank = 1
  2. high novelty / distance from the Phase-C anchor
```

This is a mechanism hypothesis, not yet a policy.

---

## 5. What is solid

### 5.1 Stage 3.5 rank-6 local rescue is real

The broad and focused evidence agree that rank-6 candidates contain real rescue opportunities.

Key evidence:

```text
broad shallow frontier harvest:
  136 / 136 cells completed
  rank-6 slice showed promising positive concentration

focused deepening join:
  rank 6: 10 / 12 better, 2 / 12 worse
```

This supports:

```text
Stage 3.5 rank-6 rescue is useful, but unsafe if widened without a guard.
```

### 5.2 The selected-start gate was safe but too lossy

The selected-start gate was:

```text
candidate rank = 6
selected_start_match_ratio >= 0.437
```

It was safe on the observed rows:

```text
kept rows: 6
kept better/worse: 6 / 0
```

But it rejected useful positives:

```text
rejected rows: 6
rejected better/worse: 4 / 2
```

Examples of rejected positives:

```text
1111/search7002 rank 6:
  +0.015 versus shallow
  +0.465 versus selected

1411/search7005 rank 6:
  +0.013 versus shallow
  +0.218 versus selected

611/search7003 rank 6:
  +0.011 versus shallow
  +0.138 versus selected

1411/search7004 rank 6:
  +0.005 versus shallow
  +0.136 versus selected
```

Conclusion:

```text
selected-start strength is a useful safety clue,
but it is too conservative as a final rule.
```

### 5.3 The softened canary passed as an implementation check

The softened canary rule was:

```text
candidate rank = 6
AND either:
  selected_start_match_ratio >= 0.437
  OR shallow_resume_minus_selected >= 0.400
```

The canary result was:

```text
4 / 4 cells completed
2 executed
2 skipped
0 policy mismatches
2 / 2 executed cells nonnegative versus shallow
```

Executed rows:

```text
1511/search7004:
  canary = 0.578
  shallow = 0.568
  +0.010 versus shallow

1111/search7002:
  canary = 0.756
  shallow = 0.741
  +0.015 versus shallow
```

This validates the canary plumbing. It does not validate a general policy.

### 5.4 The recall audit is the key boundary evidence

The recall audit reproduced five boundary rows:

```text
5 / 5 completed
0 errors
0 policy decision mismatches
3 positives versus shallow
2 regressions versus shallow
5 / 5 reproduced prior deepening exactly
```

Positive rows:

```text
1411/search7005 b47e22bc63e7c189:
  +0.013 versus shallow

611/search7003 826e5c871f444486:
  +0.011 versus shallow

1411/search7004 2632e79517bf1c7c:
  +0.005 versus shallow
```

Regression rows:

```text
1411/search7001 c7d123cf849533ee:
  -0.002 versus shallow

1111/search7004 511a29668b8c44d1:
  -0.007 versus shallow
```

This is a small boundary, but it is stable enough to explain.

---

## 6. Route-lineage audit result

The route-lineage audit found:

```text
rows: 5
positives: 3
regressions: 2
single-feature perfect separators: 0
two-feature perfect separators: 141
```

The audit reports several perfect two-feature separators.

Some use:

```text
candidate_distance_to_final_best
```

but that should not be used as the policy-facing feature, because it depends on final-artifact information.

The safer policy-facing family is:

```text
candidate_source_rank_eq_1 == 1
AND candidate_novelty_distance_to_anchor >= 173.5
```

or equivalently:

```text
candidate_source_rank_eq_1 == 1
AND candidate_distance_to_phasec_anchor >= 173.5
```

The plain-English mechanism is:

> The useful rank-6 candidate is the first phaseA-selected candidate, and it is far enough from the Phase-C anchor to offer a genuinely different local-rescue route.

The five rows fit this:

```text
positives:
  source_rank = 1
  novelty_to_anchor high

regression 1:
  source_rank = 1
  novelty_to_anchor too low

regression 2:
  novelty_to_anchor high
  source_rank != 1
```

---

## 7. Source-code findings

### 7.1 `candidate_source_rank` appears to be real saved lineage

In `stage3_two_phase.py`, Phase-C candidate rows are built before Phase-C starts and before Stage 3.5 rescue.

For Phase-A selected rows, the source code records:

```text
candidate_source = "phaseA_selected"
candidate_source_rank = selected_rank in phaseA_selected_rows order
```

This is not derived from the Stage 3.5 result.

### 7.2 `novelty_distance_to_anchor` appears to be real saved Phase-C lineage

Also in `stage3_two_phase.py`, the Phase-C start builder computes distance to the Phase-C anchor and saves:

```text
novelty_distance_to_anchor
```

This is available before the Stage 3.5 local-rescue outcome.

Therefore, the feature pair:

```text
candidate_source_rank == 1
AND high novelty_distance_to_anchor
```

is credible as a pre-runtime mechanism hypothesis.

### 7.3 `candidate_distance_to_final_best` should remain descriptive only

The route-lineage extractor computes `candidate_distance_to_final_best` from final-artifact state.

That makes it useful for posthoc explanation, but risky for policy design.

Do not use this as a runtime/actionable rule field:

```text
candidate_distance_to_final_best
```

Preferred action-safe field:

```text
candidate_novelty_distance_to_anchor
```

---

## 8. Current source-code risks

### 8.1 Missing lineage currently defaults to zero

The current route-lineage audit helper uses permissive defaults:

```text
_safe_int(... default=0)
_safe_float(... default=0.0)
```

Candidate and anchor rows are also looked up with empty-dict fallbacks.

This means missing data can quietly become:

```text
source_rank = 0
novelty_distance = 0
distance_to_anchor = 0
```

That is acceptable for a quick posthoc audit only if clearly documented.

It is not acceptable for a policy/prep extractor.

### 8.2 The audit scans both action-safe and posthoc fields

The current route-lineage audit scans some features that are safe for a future policy, and some that are descriptive/posthoc.

Action-safe candidates include:

```text
candidate_source_rank
candidate_novelty_distance_to_anchor
candidate_distance_to_phasec_anchor
```

Posthoc or outcome-adjacent fields include:

```text
candidate_distance_to_final_best
phasec_accepts
phasec_improves
audit_minus_shallow
stage35_best_score
stage35_runtime_seconds
```

A future confirmation-prep extractor must separate these categories.

### 8.3 Dedicated extractor tests are missing

There are tests for related underlying fields in the Stage 3 / Stage 3.5 system, but there does not appear to be a dedicated test file for:

```text
extract_stage35_rank6_route_lineage_boundary_audit_v1.py
```

and there are no dedicated tests proving:

```text
missing candidate row -> invalid, not reject
missing anchor row -> invalid, not reject
missing source_rank -> invalid, not reject
missing novelty_distance_to_anchor -> invalid, not reject
candidate_distance_to_final_best is not used by the action-safe rule
```

This is the main test gap.

---

## 9. Tightened science conclusion

Use this conclusion:

```text
Stage 3.5 rank-6 local rescue is a real score-improvement region.

The current softened rule is safe but too conservative.

A source-rank-plus-route-novelty hypothesis explains the five-row rejected-positive / regression boundary.

The hypothesis is mechanistically credible because source_rank and novelty_distance_to_anchor are saved before Stage 3.5 rescue.

But the current route-lineage extractor is posthoc, permissive on missing data, and not covered by a dedicated test.

Therefore this is ready for strict offline confirmation-prep, not runtime.
```

Avoid this wording:

```text
route-lineage policy is ready
```

Use this wording:

```text
route-lineage mechanism hypothesis is ready for strict offline confirmation-prep
```

---

## 10. Recommended next dev task

Do not start runtime yet.

Next task:

```text
Write a strict offline route-lineage disagreement scan.
```

Purpose:

```text
Apply the candidate route-lineage rule to all available retained rank-6 rows,
using only pre-runtime-safe lineage fields.
```

Candidate safe rule:

```text
candidate_source == "phaseA_selected"
AND candidate_source_rank == 1
AND candidate_novelty_distance_to_anchor >= 173.5
```

Do not use these fields as action-rule inputs:

```text
candidate_distance_to_final_best
phasec_accepts
phasec_improves
audit_minus_shallow
stage35_best_score
stage35_runtime_seconds
```

They may be reported as diagnostics, but they must not decide keep/reject.

---

## 11. Proposed new extractor contract

Create a new extractor, for example:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/
extract_stage35_rank6_route_lineage_confirmation_prep_v1.py
```

It should classify all available retained rank-6 rows into:

```text
A. old softened rule rejects, route-lineage rule keeps
   predicted recovered positives

B. old softened rule keeps, route-lineage rule rejects
   safety checks

C. both rules keep
   positive controls

D. both rules reject
   negative controls

E. invalid / missing lineage
   cannot classify
```

Required output summary fields:

```text
valid_row_count
invalid_row_count
invalid_reason_counts

old_softened_keep_count
old_softened_reject_count

route_lineage_keep_count
route_lineage_reject_count

rule_disagreement_count
group_A_count
group_B_count
group_C_count
group_D_count
group_E_count
```

Required row fields:

```text
fixture_seed
search_seed
candidate_rank
candidate_hash
candidate_source
candidate_source_rank
candidate_novelty_distance_to_anchor
candidate_distance_to_phasec_anchor

selected_start_match_ratio
shallow_resume_minus_selected
old_softened_keep
route_lineage_keep
confirmation_group

row_valid
invalid_reason
```

Invalid row reasons should include:

```text
missing_candidate_hash
missing_artifact_relpath
missing_phaseC_candidate_pool_rows
candidate_hash_not_found_in_pool
missing_phaseC_anchor_candidate_hash
anchor_hash_not_found_in_pool
missing_candidate_source
missing_candidate_source_rank
missing_candidate_novelty_distance_to_anchor
```

Important rule:

```text
Missing data must not become a negative decision.
Missing data must become invalid / not classifiable.
```

---

## 12. Minimum tests before runtime

Add a dedicated test file, likely:

```text
tests/tools/test_no_wli_stage35_rank6_route_lineage_confirmation_prep_v1.py
```

Minimum tests:

```text
1. source_rank=1 and novelty>=173.5 -> route_lineage_keep=1

2. source_rank=1 and novelty<173.5 -> route_lineage_keep=0

3. source_rank=3 and novelty>=173.5 -> route_lineage_keep=0

4. missing candidate row -> invalid, not reject

5. missing anchor row -> invalid, not reject

6. missing source_rank -> invalid, not reject

7. missing novelty_distance_to_anchor -> invalid, not reject

8. candidate_distance_to_final_best is ignored by the action-safe rule

9. old softened rule vs route-lineage rule group labels are assigned correctly
```

The most important test principle:

```text
missing lineage is invalid, not reject
```

---

## 13. Decision rule after confirmation-prep scan

If group A exists:

```text
old softened rule rejects, route-lineage rule keeps
```

then there may be honest predicted-recovered-positive cells for a tiny confirmation panel.

If group B exists:

```text
old softened rule keeps, route-lineage rule rejects
```

then there are useful safety checks.

If no group A or B exists:

```text
There may be no honest confirmation surface.
Close as mechanism insight or look for a broader retained-rank-6 source.
```

Only if there are honest held-out rows should the branch proceed to a tiny runtime confirmation.

Runtime confirmation, if reached later, should be:

```text
6-8 rows maximum
fixed rule
no threshold tuning
include positive controls and regression controls
review after completion
```

---

## 14. Final recommended status to carry

```text
Score-improvement direction:
  strong enough to continue

Mechanism:
  credible source-rank + anchor-novelty hypothesis

Policy readiness:
  no

Runtime readiness:
  no

Next step:
  strict offline held-out / disagreement scan using pre-runtime-safe lineage fields
```

Short dev-facing summary:

```text
Good signal. Better mechanism. Not strict enough yet. Harden offline first.
```
