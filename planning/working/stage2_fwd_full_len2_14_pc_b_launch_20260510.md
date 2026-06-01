# stage2_fwd_full_len2_14_pc_b launch note

Date: 2026-05-10

Script:
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_stage2_len2_14_pc_b.py`

Run identity:
- run label: `stage2_fwd_full_len2_14_pc_b`
- run mode: `stage2_fwd_full_len2_14`
- chunk start: `5200`
- clean chunks: `7200`
- directions: `fwd`
- score region: `full`
- active span lengths: `2..14`
- ladder profile: `v0_3_plus_long_relaxed_v2_len2_14`

Retained runtime reference:
- completed same-machine anchor: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage1_fwd_full_1k_pc_b/final_summary.json`
- anchor elapsed: `4619.5664164s`
- anchor coverage: `500` clean chunks, `18500` samples
- observed throughput: `4.004704842931328` samples/s

Sizing:
- projected samples: `266400`
- projected wallclock from anchor sample throughput: about `18.48h`
- intended wallclock budget: `18h`
- note: the projection is slightly above 18h but inside rounding/noise for this next `pc_b` cell; check first checkpoint projection before queuing any follow-on cell

Stop condition:
- stop naturally when the one configured run completes `7200` clean chunks and writes `final_summary.json`
- stop early on runner failure
- if the first checkpoint projection is materially above the `18h` budget, rescope before launching another same-family cell

Output and log targets:
- output directory: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage2_fwd_full_len2_14_pc_b`
- runner tee log: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/logs/stage2_fwd_full_len2_14_pc_b.log`
- PowerShell tee log: `output/logs/stage2_fwd_full_len2_14_pc_b_run.log`

Preflight:
- `python -m pytest tests/tools/test_phaseB_runeberg_nose_damage_ladder_v1.py`
- result: `33 passed`

Completion:
- status: `complete`
- finished at UTC: `2026-05-10T22:45:27.940914+00:00`
- elapsed: `66502.5843644s` (`18.47h`)
- samples: `266400`
- feature rows: `28771200`
- actual chunks: `7200`
- next chunk start: `12400`
- checkpoints: `533`
- observed sample throughput: `4.005859359393687` samples/s
- observed feature-row throughput: `432.6328108145182` rows/s

Save check:
- `final_summary.json`, `run_manifest.json`, `config.json`, and `run_state.json` parse with Python `json`
- `run_state.json` status is `complete`
- `timing_checkpoints.csv` has `534` lines
- `rolling_feature_summary.csv` has `534` lines
- `sample_rows.csv` has `266401` lines
- log search found no `Traceback`, `Exception`, `Error`, `failed`, `NativeCommandError`, or `unraisablehook` text in saved tee logs
- PowerShell reported an ignored interpreter-shutdown message after the runner printed completion; saved artifacts look complete
