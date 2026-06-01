# Stage-2 Topk Selected-Family Low-Edge Phase-A Gate Persistence Microprobe Note

Date: 2026-04-23

Status:

- completed
- branch-point implementation microprobe

## Scope

This note records the persistence pass for the current selector-branch gate:

- gate:
  - `phasea_rank1_init_match >= 0.30`
- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

The question here was not whether the gate existed.

It was whether the gate could be made visible during a real replay through the
repo-native Python artifacts.

## Main result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_phasea_gate_live_read_canary`

Reason:

- the Phase-A gate now has an early persisted artifact
- that artifact is surfaced in the replay wrapper status path
- the change landed without relying on bespoke launcher logic

## Cross-checked evidence

Core files:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_calls.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

New persisted artifact:

- `resume_bundle/phasea_gate_snapshot.json`

What it now records:

- rank-1 Phase-A init / final match
- best Phase-A init / final match
- rank-1 plateau-stop flag
- Phase-B gate and family-preservation context

Wrapper exposure:

- exact replay `attempt_status.json` now includes:
  - `phasea_gate_snapshot_json_relpath`

Focused verification:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_selected_family_low_edge_exact_replay_1111_7004.py -q`
- result:
  - `40 passed`

## Interpretation

This changes the branch state again.

What is now true:

- the gate is no longer only an offline reconstruction
- a real replay bundle can now expose the key Phase-A gate evidence while the
  run is still in flight
- the next honest step is no longer more persistence work

The next honest step is one cheap live-read canary:

- rerun one exact replay lane with the new snapshot path
- confirm the file appears at the expected point in wallclock
- then decide whether the first real action contract should be:
  - fallback
  - early stop
  - or both
