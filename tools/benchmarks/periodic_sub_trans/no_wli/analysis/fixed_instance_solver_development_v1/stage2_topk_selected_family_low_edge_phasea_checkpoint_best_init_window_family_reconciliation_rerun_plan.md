# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Best-Init Window Family Reconciliation Rerun Plan

Date: 2026-04-25

Purpose:
- Re-run the remaining-family microbatch after the shared role contract fix so the decisive family evidence is provenance-clean instead of reconciled from stale 2026-04-24 row/control artefacts.

Scope:
- Script: `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1.py`
- Fixed fixture: `1111`
- Search seeds: `7002`, `7003`, `7004`
- Lane roles: `filtered_family`, `kept_family`, `kept_family`
- No widening and no live runtime.

Runtime sizing:
- Same-family retained exact replay anchors in the runner:
  - `7002`: about `00:22:13`
  - `7003`: about `00:21:54`
  - `7004`: about `00:24:17`
- Anchored projected serial total: about `01:08:25`
- Intended wallclock budget: `01:30:00`

Stop condition:
- After each completed lane, recompute the projected three-lane total from observed elapsed plus remaining anchors.
- Stop before launching the next lane if the projection exceeds `01:30:00`.

Expected clean outcome:
- `7002` is judged under the filtered-family contract and has `action_behaved_as_expected = 1`.
- `7003` and `7004` are judged under the kept-family no-harm contract and have `action_behaved_as_expected = 1`.
- `matrix_run_state.json`, final `matrix_run_events.jsonl` event, rows, summary, recommendation, and readout agree on the same recommendation.

Review gate:
- Run the family provenance audit after the rerun and require zero row mismatches plus agreement across recommendation layers before any external-review packaging claim.

Outcome:
- Rerun bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T150714Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1`
- Runtime log:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/runtime_logs/20260425T150711Z__phasea_checkpoint_best_init_window_family_reconciliation_rerun.log`
- Result:
  - `7002` completed as `filtered_family`, verdict `filter`, action applied `1`, `action_behaved_as_expected = 1`.
  - `7003` completed as `kept_family`, verdict `keep`, action applied `0`, `action_behaved_as_expected = 1`.
  - `7004` was not launched because the post-7003 projected total was `01:56:44`, over the `01:30:00` budget.
  - The microbatch stopped with status `stopped_over_budget`, completed jobs `2/3`, and recommendation `hold`.
- Provenance audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T164730Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1`
  - Row mismatch count: `0`.
  - Recommendation values match: `1`.
  - Bundle complete: `0`.
  - Audit recommendation: `hold`.

Close-out:
- The role-label provenance defect is fixed for the completed rerun rows.
- The rerun does not produce a complete external-review-ready family pack because it stopped over budget before `7004`.
- Do not widen or package as review-ready from this partial rerun.
