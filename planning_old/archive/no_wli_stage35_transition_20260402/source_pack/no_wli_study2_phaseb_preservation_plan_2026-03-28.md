# Study 2 Implementation Plan: Phase-B Family Preservation

## 1. Why Study 2 Is Next

Study 1 closed as a valid negative on `seed211`.

- widened Stage-3 entry executed correctly
- solve did not move
- downstream family counters did not move

Study 3 then closed as a valid negative on `seed411`.

- isolated Phase-C start balancing executed correctly
- Phase-C candidate pool stayed unchanged, as intended
- actual Phase-C starts stayed unchanged
- solve did not move

That shifts the next bottleneck earlier in the downstream path:

- not Stage-3 entry depth by itself
- not Phase-C start order by itself
- but preservation of distinct useful families before Phase-C start allocation

Current working seed split remains:

- `211`:
  - mainly upstream reach / `good_family_absent`
- `411`:
  - mainly downstream preservation / `good_family_undervalued`

So Study 2 should target `seed411` first.

## 2. Study 2 Hypothesis

If `seed411` is failing because distinct useful families are being compressed too
early in Phase-B selection, then reserving some downstream slots by family view
before final global fill should preserve more distinct startable families into
Phase-C and may improve `best_match_ratio`.

This is not a claim that family-preserving selection will solve the tier by
itself. It is a claim that current row-first Phase-B compression may be too
aggressive for `411`-like cases.

## 3. Exact Intervention Boundary

Study 2 v1 should change only:

- Phase-B to Phase-C carry-forward selection

Study 2 v1 should not change:

- Stage-3 entry policy
- Phase-A basin generation
- Phase-B scoring key
- Phase-B tie-band widening logic
- Phase-C rescue logic
- Stage-3.5 logic

In other words:

- keep Phase-B ranking exactly as it is
- but alter how the selected Phase-B rows are preserved into the downstream pool
  so that more than one family can survive when the pool supports it

## 4. Preferred Family Views

Do not invent a new family definition ad hoc.

Start from existing reviewed audit views in:

- `tools/benchmarks/periodic_sub_trans/no_wli/audit_basin_family_diversity_alignment.py`

Preferred starting candidates:

1. `prefix_hamming_le_24`
2. `near_tail_h1`

Reason:

- these views already exist in the audited tooling
- they are explicit and reproducible
- they are already part of the reviewer discussion

## 5. Recommended Study 2 v1 Policy

Minimal policy target:

- `phaseb_family_preservation_policy = reserve_by_family_v1`

Minimal behavior:

1. compute the ordinary Phase-B ranked rows exactly as today
2. define family ids for eligible Phase-B rows using one fixed family view
3. reserve a small number of slots for distinct families before final global fill
4. fill the rest of the downstream pool using the existing global order

Recommended first reservation rule:

- always keep the global top row
- then reserve up to `N` additional rows from distinct families
- then fill remaining downstream slots from the existing ordered list

Recommended first `N`:

- `2`

Reason:

- large enough to matter if collapse is real
- still small enough to keep interpretation clean

## 6. What to Measure

Primary readouts after implementation:

- `phaseB_selected_unique_end_hash`
- `phaseC_candidate_pool_unique_end_hash`
- `phaseC_start_unique_end_hash`
- `phaseC_candidate_pool_source_counts`
- `phaseC_start_source_counts`
- `best_match_ratio`
- `stage3_match_ratio`

## 18. First Live Readout Outcome

The first v39 live compare completed, but it did not satisfy the full
readout standard yet.

Completed runs:

- control:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T020350857797Z__bench_solve_pipeline_no_wli__55b7159`
- candidate:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T060445115113Z__bench_solve_pipeline_no_wli__55b7159`

What is already clear:

- the intended config delta was present
- visible solve outcome did not improve
- visible Phase-C pool and start counters did not change
- `phasec_start_checkpoints.jsonl` showed the same six starts in the same order

What is not yet acceptable:

- the Study 2 family telemetry did not persist into the saved artifact path
- the missing saved fields mean the run cannot yet answer the key question:
  - did family reservation apply and later collapse
  - or did it never change downstream composition at all

Therefore the immediate next step is not a new science study.

It is:

1. fix persistence of the Study 2 family telemetry into saved artifacts
2. rerun the same v39 compare
3. then lock the Study 2 scientific outcome

## 19. Persistence Patch Status

The persistence patch is now complete.

What was missing:

- Study 2 family telemetry was not surviving into:
  - `stage3_diagnostics`
  - `best/best_instance.json`
  - `stages.json`

Patch surfaces:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`

Regression proof:

- diagnostics serialization now tested in:
  - `tests/tools/test_no_wli_truth_diagnostics.py`
- iteration-flow propagation now tested in:
  - `tests/tools/test_no_wli_stage35_substitution_solver.py`

Post-fix proof slice:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_artifact_resume.py -q`
  - outcome:
    - `56 passed`

Next step remains unchanged:

- rerun the same v39 control-vs-candidate Study 2 compare
- `phaseC_final_winner_source`

New Phase-B family telemetry should also be added for Study 2:

- `phaseB_family_view_id`
- `phaseB_family_count_in_top_band`
- `phaseB_family_preserved_count`
- `phaseB_family_preservation_policy`
- `phaseB_family_reserved_slots`

## 7. Success and Falsification

Valid positive:

- family-preservation telemetry shows more than one family was actually carried
- Phase-C pool / starts become more diverse
- solve improves on `seed411`

Valid negative:

- family-preservation telemetry proves distinct families were carried
- downstream diversity rises
- solve still does not improve

Invalid result:

- Phase-B scoring order changed
- tie-band logic changed
- Phase-C rescue behavior changed
- family view is not recorded explicitly in config / lock / stage telemetry

## 8. Required Canaries

Before any long run, Study 2 should have:

1. preset / config / lock canary proving the new family-preservation policy is
   explicit in runtime state and emitted outputs
2. deterministic unit test on synthetic Phase-B rows proving:
   - current policy compresses to same-family rows
   - Study 2 policy preserves at least one additional family when available
3. short integration-style test proving:
   - Phase-B ranking order itself is unchanged
   - only downstream preservation differs

## 9. First Long Compare After Implementation

Once Study 2 exists, the first live compare should be:

- seed:
  - `411`
- control:
  - `stage3_preserve_tieband_probe_p9`
- candidate:
  - a new Study 2 preset that differs only by:
    - `phaseb_family_preservation_policy = reserve_by_family_v1`
    - one fixed family view id
    - one fixed reserved-slot count

Do not bundle Study 2 with:

- new rescue changes
- new Phase-C changes
- new Stage-3 entry changes

## 10. Bottom Line

The current evidence says the next meaningful intervention is:

- preserve more distinct families earlier in the downstream path

So the next phase should be:

1. implement isolated Study 2 Phase-B family preservation
2. add canaries and deterministic proof
3. hand off one narrow `seed411` control-vs-candidate long compare

## 11. Locked v1 Implementation Boundary

Study 2 v1 should preserve more family variety into the downstream pool without
changing the actual Phase-B run or the Phase-C rescue logic.

That means the runtime change should happen here:

- after ordinary Phase-B ranking and tie-band selection are already complete
- before the final `phaseA_selected` rows are appended into the Phase-C
  candidate pool

Study 2 v1 should therefore:

- leave the Phase-B run seeds unchanged
- leave `phaseB_topk` generation unchanged
- change only the downstream carry-forward list currently appended as
  `phaseA_selected`

This keeps the intervention narrower than a Phase-B ranking rewrite while still
testing the claimed downstream preservation bottleneck.

## 12. Locked v1 Policy Choice

First implementation target:

- `phaseb_family_preservation_policy = reserve_by_family_v1`
- `phaseb_family_view_id = prefix_hamming_le_24`
- `phaseb_family_reserved_slots = 2`

Locked v1 behavior:

1. keep the ordinary global top row
2. build family ids on the ranked unique-basin Phase-B rows
3. reserve up to 2 additional downstream carry-forward rows from distinct
   families
4. fill remaining downstream carry-forward slots using the existing global order
5. keep the downstream carry-forward count equal to the ordinary selected count

This is intentionally narrower than changing Phase-B seed selection itself.

## 13. Shared Family-View Source Of Truth

Do not copy the family-view logic directly into `stage3_two_phase.py`.

Implementation should use one shared helper module for:

- `FAMILY_VIEWS`
- family-view lookup by id
- `cluster_family_ids(...)`

Then:

- the audited basin-family tooling should import from that helper
- the runtime Study 2 code should import from that helper

This avoids definition drift between audit and runtime.

## 14. Concrete File Surfaces

Expected code surfaces for Study 2 v1:

- shared helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/...`
- runtime policy and telemetry:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- explicit runtime/config plumbing:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runtime_defaults.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/profile_defaults.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_calls.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_lock_payload.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

## 15. Required Test Pattern

Before any long run, Study 2 v1 should have:

1. deterministic synthetic test proving the family-preservation policy changes
   downstream carry-forward composition without changing ranking order
2. preset/config/lock/runtime canary proving the new policy, family view, and
   reserved-slot count are explicit in:
   - live runner state
   - `run_config.json`
   - non-scoring lock payload
   - Stage-3 runtime context
3. short proof slice covering:
   - the new deterministic Study 2 test
   - the new canary
   - existing Stage-3 Phase-C tests touched by the policy surface
   - fixture-matrix runtime materialization for the new control-vs-candidate lane

## 16. First Post-Implementation Long Compare

After the canary passes, the next long compare should be:

- seed:
  - `411`
- control:
  - `stage3_preserve_tieband_probe_p9`
- candidate:
  - one new Study 2 preset differing only by:
    - `phaseb_family_preservation_policy = reserve_by_family_v1`
    - `phaseb_family_view_id = prefix_hamming_le_24`
    - `phaseb_family_reserved_slots = 2`

No other Study 1 or Study 3 knobs should move in that compare.

## 17. Status Update: Study 2 Ready For Live Readout

Study 2 v1 is now implemented.

What was added:

- shared family-view helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/family_views.py`
- runtime family-preservation policy and telemetry in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- explicit runtime/config/lock/resume/preset plumbing across the planned
  surfaces in this document
- new control-vs-candidate fixture lane:
  - `stage3_preserve_tieband_probe_p9`
  - `stage3_phaseb_family_preserve_p9`

What the local proof now establishes:

1. deterministic synthetic Phase-B rows can trigger distinct-family downstream
   preservation under `reserve_by_family_v1`
2. the Study 2 policy, family view, and reserved-slot count are explicit in:
   - live runtime state
   - `run_config`
   - non-scoring lock payload
   - runtime call bridge
   - resume-parsed runtime context
3. the active v39 fixture lane materializes exactly as the intended `seed411`
   2-job compare

Proof commands:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - outcome:
    - `30 passed`
- broader confirmation:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py -q`
  - outcome:
    - `95 passed`

Prepared long-run control files:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v39_p9c3_seed411_phaseb_family_compare_2job.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v39_p9c3_seed411_phaseb_family_compare_2job.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v39_p9c3_seed411_phaseb_family_compare_2job.json`

Readout should now focus on:

- `phaseB_family_count_in_top_band`
- `phaseB_family_preserved_count`
- `phaseB_family_reservation_applied`
- `phaseB_downstream_selected_count`
- `phaseB_downstream_selected_unique_end_hash`
- `phaseC_candidate_pool_unique_end_hash`
- `phaseC_start_unique_end_hash`
- `phaseC_start_source_counts`
- `best_match_ratio`
- `stage3_match_ratio`
