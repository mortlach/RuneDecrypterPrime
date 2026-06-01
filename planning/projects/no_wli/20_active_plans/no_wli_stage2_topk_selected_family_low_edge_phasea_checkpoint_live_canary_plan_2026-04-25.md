# Stage-2 Selected-Family Phase-A Checkpoint Live-Canary Plan

Date: 2026-04-25

Status:

- closed after live-canary reconciliation

Parent closed subtopic:

- review-ready after provenance reconciliation

Runtime status:

- live runtime still blocked
- no further canary should launch from this branch
- any further runtime must be a separate timing-risk follow-up with its own
  budget and stop condition

Production / general policy:

- not claimed

## Carried Result

The previous selector-checkpoint subtopic is closed as review-ready after
provenance reconciliation.

Carried contract:

- fixed family:
  - `1111/search7001-7005`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`
- family view:
  - `prefix_hamming_le_24`
- checkpoint:
  - restart `32`
- field:
  - `phaseA_best_init_match`
- threshold:
  - `0.3865`
- `filter` action:
  - fallback to retained baseline
  - early stop selected-family attempt
- `keep` action:
  - no action
  - continue selected-family attempt

Carried family interpretation:

- `7001/7002`:
  - collapse-like selected-family lanes
  - expected verdict `filter`
- `7003/7004/7005`:
  - viable / no-harm selected-family lanes
  - expected verdict `keep`

Use this wording:

- viable selected-family lanes
- no-harm keep lanes
- collapse lanes

Avoid this wording:

- lanes where the selector helps

Reason:

- `7004` is not clearly better than baseline, so it should be treated as a
  viable/no-harm keep lane rather than a positive selector-help lane

## Purpose

This branch is not threshold tuning.

This branch is not selector development.

This branch is not Stage-3.5 rescue development.

Question:

- can the reviewed restart32 `phaseA_best_init_match` checkpoint be observed
  and audited safely in one live canary, without changing the rule or widening
  the claim?

General mechanism under test:

- an early Phase-A checkpoint should be able to detect selected-family collapse
  soon enough to avoid wasting runtime, while preserving selected-family lanes
  that remain viable

The operational test must remain one specific canary.

## Non-Goals

Do not do these in this branch:

- do not tune threshold `0.3865`
- do not retune restart count `32`
- do not try alternative Phase-A fields
- do not add new selector variants
- do not combine this with Stage-3.5 rescue work
- do not run a broad matrix
- do not reopen live runtime generally
- do not promote this as production policy
- do not claim generality beyond the tested canary

## Hypothesis

A collapse-like selected-family lane will show:

- `phaseA_best_init_match < 0.3865` by restart `32`
- verdict `filter`
- fallback plus early stop
- retained baseline outcome preserved
- material runtime saved

## Main Alternative

The fixed-family replay checkpoint may be too fitted to the retained
`1111/search7001-7005` replay family, or the live runtime evidence surface may
not be clean enough to support action decisions.

If that happens, the rule remains replay-valid only and live runtime stays
blocked.

## Mechanism Layer

- selection
- local rescue

More specifically:

- the checkpoint tests whether the selected upstream family remains viable
  after early Phase-A search, before spending more runtime on a collapsed
  selected path

## Frozen Canary Cell

Preferred first canary:

- fixture / fixed seed:
  - `1111`
- search seed:
  - `7002`
- lane type:
  - filtered collapse lane
- expected verdict:
  - `filter`
- expected action:
  - fallback plus early stop
- baseline expectation:
  - final/current resume score should match retained baseline within existing
    tolerance

Reason:

- `7002` has the clearest safety contract:
  - selected path collapsed in the retained replay evidence
  - fallback target is retained baseline
  - expected benefit is runtime saving
  - harm is easy to detect against baseline

Avoid first:

- a `7004`-like kept timing canary

Reason:

- the `7004` slowdown was bounded well enough not to invalidate the checkpoint
  contract, but its runtime cause was not fully explained
- it should only be used first if the branch is explicitly a timing-risk probe

## Required Checkpoint Fields

A live canary is allowed only if the harness can emit and audit:

- run id
- fixture id / fixed seed
- search seed
- selector id
- family view id
- checkpoint restart count
- `phaseA_best_init_match`
- threshold
- computed gate verdict
- expected gate verdict
- baseline best/resume score
- selected-path/reference score, if applicable
- current resume score
- action decision id
- action applied flag
- fallback target
- `action_stop_now`
- `action_fallback_to_baseline`
- elapsed seconds at checkpoint
- elapsed share at checkpoint
- final status
- final recommendation

## Required Artefact Layers

The output bundle must include:

- `matrix_run_state.json`
- `matrix_run_events.jsonl` with final `run_finished` event
- `*_rows.csv`
- `*_summary.json`
- `*_recommendation.json`
- `*_readout.md`
- row-level recomputation / provenance audit

Hard audit rule:

- the canary is not interpretable unless all required artefact layers are
  present and agree

## Runtime Budget

Maximum runtime per canary:

- `08:00:00`

Review cadence:

- review after every canary
- no automatic second run

If the canary does not produce useful checkpoint evidence within the budget:

- recommendation `hold`

Runtime launch discipline:

- do not launch a broad matrix
- do not launch a second canary automatically
- before launch, refresh or consult the retained-runtime wallclock reference
  and record why the single canary fits the `08:00:00` cap
- launch any approved long canary in a separate PowerShell window with
  repo-relative logs and human-readable progress

## Day 1 - Freeze The Canary Contract

No long runtime.

Deliverable:

- this active-plan file

The plan freezes:

- exact canary cell
- selector
- family view
- checkpoint field
- threshold
- action contract
- max runtime
- success/failure gates
- audit outputs

Day 1 pass condition:

- a reviewer can read this plan and know exactly what will run, what will be
  recorded, and what counts as pass/fail

## Day 2 - Inspect Or Build The Canary Harness

No full `08:00:00` canary unless the harness already exists and passes cheap
checks.

Tasks:

1. Inspect the current action-microprobe and live-action path.
2. Confirm it can run one canary cell, not a matrix.
3. Confirm the checkpoint contract is pinned and cannot drift by config.
4. Confirm all required fields are emitted.
5. Confirm the provenance audit can run on the produced bundle.
6. Add refusal checks for missing checkpoint fields.
7. Add refusal checks for missing recommendation layers.

The harness must refuse to run or must produce `hold` if:

- selector id is missing
- family view id is missing
- checkpoint restart count is missing
- `phaseA_best_init_match` is missing
- threshold is missing
- action decision cannot be recomputed
- fallback target is ambiguous
- output bundle lacks state/event/summary/recommendation/readout layers

Day 2 pass condition:

- the harness proves it can emit and audit the fields needed to judge a live
  checkpoint decision

Day 2 result:

- passed
- preflight bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T220602Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight_v1/`
- recommendation:
  - `advance`
- failed checks:
  - `none`
- runtime launched:
  - `0`
- launch guard:
  - `LIVE_CANARY_LAUNCH_APPROVED = False`
- direct runner execution currently returns:
  - `launch_blocked`
  - recommendation `hold`
- Day 3 launch wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_open_terminal_2026-04-25.ps1`
- wrapper log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_2026-04-25.log`
- wrapper cap:
  - `08:00:00`

If this condition is not met:

- do not launch the live canary
- fix the harness/audit first

## Day 3 - Run One Canary

Run exactly one canary.

Do not run a matrix.

Do not tune anything after seeing partial output.

Suggested run label:

- `stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1`

Pass criteria for the filtered-lane canary:

- status completed or cleanly early-stopped
- checkpoint restart count `32`
- `phaseA_best_init_match < 0.3865`
- observed verdict `filter`
- action applied `1`
- `action_stop_now = 1`
- `action_fallback_to_baseline = 1`
- fallback target is retained baseline
- current/final resume score equals baseline score within existing tolerance
- saved runtime is material
- all recommendation layers are present
- all recommendation layers match
- row-level recomputation mismatch count `0`

Fail / hold criteria:

- any required field missing
- checkpoint decision not recomputable
- fallback target missing or ambiguous
- state/event/summary/recommendation/readout disagree
- row mismatch count greater than `0`
- run exceeds `08:00:00` without usable checkpoint evidence
- action applied but final state cannot be tied to baseline fallback
- unexpected keep/filter verdict relative to canary expectation without a clear
  evidence explanation

Day 3 review question:

- did the live canary produce a trustworthy, auditable checkpoint decision?

Do not use this review question:

- did the run solve the cipher?

Solving is not the point of this branch.

## Day 4 - Review And Branch Decision

No automatic runtime.

Choose one:

- advance:
  - one more canary is justified
  - prefer a complementary kept/no-harm canary
  - still `08:00:00` max
  - still no threshold tuning
- hold:
  - checkpoint remains replay-valid, but live evidence/harness is not clean
  - fix audit/harness before more runtime
- close:
  - live canary shows the replay checkpoint is not safe or not interpretable
  - preserve replay-family result only
  - keep live runtime blocked

If Day 3 passed as a filtered canary, the next canary may be kept/no-harm, but
should still avoid known timing-risk cases unless explicitly labelled as a
timing-risk probe.

Day 3 result:

- source bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T004304Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
- audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T012105Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`
- source recommendation:
  - `advance`
- audit recommendation:
  - `advance`
- row mismatch count:
  - `0`
- recommendation layers:
  - state `advance`
  - final event `advance`
  - summary-derived `advance`
  - recommendation JSON `advance`
  - readout `advance`
- first live canary decision:
  - passed
- launch guard after run:
  - reset to `LIVE_CANARY_LAUNCH_APPROVED = False`
- non-blocking note:
  - the source readout markdown has a stale `final status: running` line from
    write order; state/final event/row/summary/recommendation/audit all show
    completed and advance, and the runner write order has been fixed for
    future runs

Complementary kept/no-harm canary result:

- source bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014422Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
- audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T021629Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`
- source recommendation:
  - `advance`
- audit recommendation:
  - `advance`
- row mismatch count:
  - `0`
- recommendation layers:
  - state `advance`
  - final event `advance`
  - summary-derived `advance`
  - recommendation JSON `advance`
  - readout `advance`
- result:
  - kept/no-harm semantic pass
  - selected path preserved
  - `phaseA_best_init_match = 0.490`
  - verdict `keep`
  - action applied `0`
  - current/reference selected-path match `0.476 / 0.476`
- timing caveat:
  - reference exact replay elapsed `00:21:54`
  - kept live canary elapsed `00:30:51`
  - delta `+537.015s`
  - ratio about `1.409x`
- operational note:
  - one accidental bare-process partial launch was stopped and marked
    `interrupted_before_wrapper_relaunch`; it is not used as evidence
- launch guard after run:
  - reset to `LIVE_CANARY_LAUNCH_APPROVED = False`

Reconciliation decision:

- note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_reconciliation_note_2026-04-26.md`
- decision:
  - close this live-canary branch as semantically passed and provenance-clean
  - carry a kept-lane timing caveat
  - do not widen in this branch
  - do not reopen live runtime generally
  - if continuing, open a separate timing-risk follow-up rather than launching
    another checkpoint canary

## Review Template

Each canary review should answer:

1. What ran?
2. Did it stay within the `08:00:00` budget?
3. Was the checkpoint reached?
4. Were all required fields emitted?
5. What was `phaseA_best_init_match` at restart `32`?
6. What verdict was computed?
7. Was action applied?
8. If filtered, did it fall back to baseline?
9. If kept, did it preserve the selected path?
10. Did all artefact layers agree?
11. Did row-level recomputation pass?
12. Was any timing anomaly observed?
13. Decision: advance / hold / close.

## Expected Evidence Files

Expected files:

- `matrix_run_state.json`
- `matrix_run_events.jsonl`
- `*_rows.csv`
- `*_summary.json`
- `*_recommendation.json`
- `*_readout.md`
- `*_provenance_audit_summary.json`
- `*_provenance_audit_rows.csv`
- `*_provenance_audit_readout.md`

Minimum machine-readable fields:

- `search_seed`
- `lane_role`
- `observed_gate_verdict`
- `expected_gate_verdict`
- `phasea_gate_action_applied`
- `gate_checkpoint_restart_count`
- `phaseA_best_init_match`
- `current_resume_best_match_ratio`
- `baseline_best_match_ratio`
- `reference_resume_best_match_ratio`
- `delta_vs_baseline`
- `delta_vs_reference_candidate`
- `actual_saved_attempt_seconds`
- `actual_saved_attempt_share`
- `action_behaved_as_expected`
- `recomputed_action_behaved_as_expected`
- `row_mismatch`

## Safety And Interpretation Rules

1. A clean canary does not reopen live runtime generally.
2. A clean canary does not make `0.3865` a universal threshold.
3. A clean canary does not prove the selector is generally good.
4. A failed canary does not invalidate the fixed-family replay result.
5. Missing provenance is a `hold`, not an interpretation exercise.
6. Any mismatch between state/event/summary/recommendation/readout is a `hold`.
7. Any unknown lane role should fail loudly.

## What Counts As Learning

This branch learns something useful if it answers any of these:

- can restart32 Phase-A evidence be observed cleanly in live runtime?
- can a selected-family collapse be filtered without score harm?
- can the action trail be audited without provenance drift?
- is fallback plus early stop operationally safe enough for a second canary?
- does live runtime expose missing fields not visible in replay?

This branch does not need to prove generality.

## Close-Out Wording If Day 3 Passes

The first live canary produced a complete and auditable checkpoint decision
under the reviewed restart32 `phaseA_best_init_match` contract. The result
supports one further narrow canary, but does not reopen live runtime generally
and does not promote the checkpoint as a production policy.

## Close-Out Wording If Day 3 Fails

The replay-family checkpoint remains review-ready after provenance
reconciliation, but the live canary did not produce a clean enough evidence
surface for runtime use. Live runtime remains blocked. Next work should fix the
harness/audit gap before any further checkpoint experiment.

## Final Instruction

Do not start a broad matrix or tune the threshold.

Prepare one live-canary branch with the reviewed contract unchanged:

- restart `32`
- `phaseA_best_init_match`
- threshold `0.3865`
- `filter = fallback + early stop`
- `keep = no action`

Use an `08:00:00` cap.

Run one canary only.

Review before any second canary.
