# Stage-2 Topk Selected-Family Low-Edge Exact Replay Closure Note: 1111/search7004

Date: 2026-04-23

Status:

- closed
- clean exact negative

## Scope

This note closes the first exact execution gate for the narrowed upstream
selector:

- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

Exact replay bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

This note closes this exact replay shape.

It does not prove that every upstream representative-selection idea is false.

## Why this study existed

This was the smallest honest first execution gate after the selector branch had
already passed the cheap offline steps:

- promoted-family audit
- concrete selector audit
- family-view / score-band sensitivity sweep
- saved handoff audit

The science-method role was simple:

- before spending more runtime, test whether the saved handoff truth lift
  survives one exact Stage-3 execution lane
- if it does not, move to a cheaper postmortem explanation before any second
  replay or runtime

## Hypothesis block

Question:

- on fixed `1111/search7004`, does replacing the saved representative with
  `selected_family_low_edge_eps_0p016_v1` improve the executed Stage-3 replay?

Suspicion:

- `1111/search7004` is a real upstream representative-selection miss
- the saved handoff improvement is large enough to survive exact execution

Main alternative:

- the selector improves the saved handoff but the execution lane stays flat or
  worse

Decision rule:

- advance only if the replay completes honestly and beats retained baseline
  cleanly
- refine only for a narrow gain or a budget-fragile positive
- close if the replay is flat or worse

## What happened

Runtime:

- started:
  - `2026-04-23T04:24:29Z`
- finished:
  - `2026-04-23T05:32:22Z`
- elapsed:
  - `01:07:53`

Completion evidence:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/attempt_status.json`
- fields:
  - `status = "completed"`
  - `completed = 1`
  - `elapsed = "01:07:53"`
  - `resume_bundle_written = 1`

## Cross-checked result

Run summary:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/run_summary.json`
- fields:
  - `baseline_best_match_ratio = 0.423`
  - `retained_stage3_reference_match_ratio = 0.432`
  - `resume_best_match_ratio = 0.420`
  - `match_delta_vs_baseline = -0.003`
  - `match_delta_vs_retained_stage3_reference = -0.012`

Selector-specific summary:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/selected_family_low_edge_exact_replay_summary.json`
- fields:
  - `baseline_row_id = "stage2_topk:1"`
  - `baseline_row_truth_match = 0.091`
  - `candidate_row_id = "stage2_topk:5"`
  - `candidate_row_truth_match = 0.161`
  - `candidate_truth_delta_vs_baseline_row = 0.070`
  - `candidate_init3_count = 64`
  - `candidate_stage3_promoted_keys_count = 144`
  - `resume_best_stage = "stage3_full_refine"`

So the selector was real at handoff:

- saved-row truth improved from `0.091` to `0.161`
- the Stage-3 input surface changed materially

But it still lost on exact execution:

- exact replay best:
  - `0.420`
- artifact baseline:
  - `0.423`
- retained Stage-3 reference:
  - `0.432`

## Phase-C read

Checkpoint stream:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/resume_bundle/phasec_start_checkpoints.jsonl`

Key start summary:

- start `1`
  - source:
    - `stage3_best_phaseB`
  - bucket:
    - `anchor`
  - init `0.182`
  - final `0.181`
- start `2`
  - source:
    - `phaseA_selected`
  - source rank:
    - `1`
  - init `0.415`
  - final `0.420`
  - `became_global_best = 1`
  - `overtook_anchor = 1`
  - `plateau_would_stop = 1`
- starts `3-6`
  - final matches:
    - `0.071`
    - `0.043`
    - `0.042`
    - `0.220`

Interpretation:

- the selector did create a strong challenger lane
- that lane almost reproduced the retained stable `0.420` region
- but it still did not beat either the artifact baseline or the retained
  Stage-3 reference

## Logging and persistence read

The direct Python replay now emits enough repo-native progress and rescue
artifacts to inspect or stop the run without an external launcher.

Verified outputs:

- `attempt_status.json`
- `resume_bundle/stage2_resume.json`
- `resume_bundle/stage3_prep.json`
- `resume_bundle/stage3_resume_status.json`
- `resume_bundle/stage3_resume_progress.jsonl`
- `resume_bundle/phasec_start_checkpoints.jsonl`

This matters because future IDE-run investigations can now be judged from
in-app persisted progress rather than bespoke terminal wrappers.

## Decision

Decision on this exact replay:

- `close`

Meaning:

- close the first exact execution gate for
  `selected_family_low_edge_eps_0p016_v1`
- do not schedule a second replay or live runtime on habit
- treat the selector as execution-active but not solve-improving on the first
  exact gate

## Carry-forward lesson

The upstream selector line is now narrower, not broader:

- the saved handoff truth gain is real
- the selector can create a strong execution challenger lane
- the gain still collapses before final replay victory

So the next honest move is cheaper, not bigger:

- an offline execution-collapse / postmortem audit
- not another generic selector sweep
- not another family-diversity runtime
- not another entry-allocation runtime
- not a second exact replay by default
