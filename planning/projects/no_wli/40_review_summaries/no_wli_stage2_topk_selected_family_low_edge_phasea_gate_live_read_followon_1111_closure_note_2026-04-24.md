# Stage-2 Topk Selected-Family Low-Edge Phase-A Gate Live-Read Follow-On Closure Note

Date: 2026-04-24

Status:

- completed
- advance on live-read correctness
- refine on action timing

## Why this note exists

The selector branch had already established:

- an offline gate:
  - `phasea_rank1_init_match >= 0.30`
- an operational savings read:
  - about `42.3` filtered saved attempt minutes
- a first live-read canary failure mode:
  - the snapshot file existed
  - but the key gate fields were `null`

This note closes the next honest family step:

- rerun the patched `1111/search7004` canary once
- then complete the remaining fixed `1111` family cells
- and ask whether the live gate surface is both usable and family-correct

## Runs

- patched predecessor canary:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061020Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- family follow-on:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1.py`
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1/`

## Outcome

- patched `7004` canary:
  - completed in:
    - `00:23:56`
  - replay result stayed the same local negative:
    - baseline `0.423`
    - retained Stage-3 reference `0.432`
    - replay `0.420`
    - delta vs baseline `-0.003`
  - the snapshot became usable:
    - `phaseA_rank1_init_match = 0.415`
    - `phaseA_best_init_match = 0.415`
    - `phaseA_best_final_match = 0.415`
    - gate verdict:
      - `keep`
  - snapshot timing:
    - elapsed:
      - `1261.0s`
      - about `21m01s`
    - share of total elapsed:
      - `0.878`
- full family follow-on:
  - completed in:
    - `02:03:21`
  - coverage:
    - `5 / 5` family cells
  - machine recommendation:
    - `advance`
  - snapshot presence:
    - `5 / 5`
  - snapshot usability:
    - `5 / 5`
  - verdict agreement with the known split:
    - `5 / 5`
  - reproduced split:
    - keep:
      - `7003`
      - `7004`
      - `7005`
    - filter:
      - `7001`
      - `7002`

## Per-seed live gate read

- `7004`
  - `phasea_rank1_init_match = 0.415`
  - verdict:
    - `keep`
  - replay delta vs baseline:
    - `-0.003`
- `7001`
  - `phasea_rank1_init_match = 0.254`
  - verdict:
    - `filter`
  - replay delta vs baseline:
    - `-0.267`
- `7003`
  - `phasea_rank1_init_match = 0.490`
  - verdict:
    - `keep`
  - replay delta vs baseline:
    - `+0.068`
- `7005`
  - `phasea_rank1_init_match = 0.395`
  - verdict:
    - `keep`
  - replay delta vs baseline:
    - `+0.041`
- `7002`
  - `phasea_rank1_init_match = 0.289`
  - verdict:
    - `filter`
  - replay delta vs baseline:
    - `-0.444`

## Timing caveat

The family live-read passed on correctness, but not yet on early action timing.

- mean snapshot elapsed:
  - `1303.4s`
  - about `21m43s`
- mean snapshot share of total elapsed:
  - `0.881`

So this branch now proves:

- the persisted live gate is real
- the persisted live gate is usable
- the persisted live gate reproduces the known keep/filter split

But it does not yet prove:

- that the current emitted snapshot is early enough to recover the previously
  estimated filtered-lane wallclock savings in a real action wrapper

## Decision

- close the live-read validation branch as a semantic pass
- do not reopen the old question of whether the live gate exists or matches the
  family split
- carry forward the remaining open action question instead:
  - should the first automated gate action be:
    - fallback
    - early stop
    - or both
- and carry forward the remaining instrumentation question:
  - can the gate verdict be emitted at the actual decision point rather than at
    about `0.88` of total replay wallclock
