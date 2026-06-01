# Stage-2 Topk Selected-Family Low-Edge Phase-A Gate Live-Read Canary Note

Date: 2026-04-24

Status:

- completed
- refine
- follow-on blocked pending one patched rerun

## Why this note exists

The selector branch had already proven:

- an offline gate:
  - `phasea_rank1_init_match >= 0.30`
- operational value:
  - about `42.3` filtered saved minutes
- replay-bundle persistence:
  - `resume_bundle/phasea_gate_snapshot.json`

This canary was the first real IDE-style replay intended to prove that the
persisted snapshot was also usable as a live decision surface.

## Run

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T034213Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`

## Outcome

- completion:
  - `attempt_status.json`
  - `status = "completed"`
  - `elapsed = "01:00:17"`
- replay result stayed the same local negative:
  - baseline `0.423`
  - retained Stage-3 reference `0.432`
  - replay `0.420`
  - delta vs baseline `-0.003`
- the snapshot artifact did exist:
  - `resume_bundle/phasea_gate_snapshot.json`
- but the live gate payload was not yet usable:
  - `phaseA_rank1_init_match = null`
  - `phaseA_best_init_match = null`
  - `phaseA_rank1_final_match = null`
- snapshot timing was also late:
  - snapshot timestamp:
    - `2026-04-24T04:35:55Z`
  - attempt start:
    - `2026-04-24T03:42:13Z`
  - snapshot elapsed:
    - about `3222s`
    - about `53m42s`
  - snapshot share of total run:
    - about `0.891`

## Interpretation

- this was a valid persistence smoke test:
  - the file exists
  - the wrapper relpath exists
  - the progress event exists
- this was not yet a valid actionability pass:
  - the gate metric fields were empty because the snapshot builder was reading
    the wrong row schema
  - the snapshot also appeared too late to count as a proven stop / fallback
    surface

## Immediate follow-up

The code fix is now landed in:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`

It backfills the gate snapshot from the real Phase-A row schema:

- `end_match`
- `best_delta_pct`
- `phaseb_rank`
- `selection_bucket`

Focused verification after the fix:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_selected_family_low_edge_exact_replay_1111_7004.py tests/tools/test_no_wli_phasea_gate_live_read_followon_1111_v1.py -q`
- result:
  - `45 passed`

## Decision

- do not launch the 8-hour family follow-on yet
- rerun the single `7004` live-read canary once with the patched snapshot
- only if that rerun writes a usable gate metric should the longer
  `7001/7003/7005/7002` follow-on be treated as launch-ready
