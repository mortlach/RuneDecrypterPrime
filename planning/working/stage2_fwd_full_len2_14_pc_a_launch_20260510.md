# stage2_fwd_full_len2_14_pc_a launch note

Date: 2026-05-10

Script:
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_stage2_len2_14_pc_a.py`

Run identity:
- run label: `stage2_fwd_full_len2_14_pc_a`
- run mode: `stage2_fwd_full_len2_14`
- chunk start: `1000`
- clean chunks: `4200`
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
- projected samples: `155400`
- projected wallclock from anchor sample throughput: about `10.78h`
- intended wallclock budget: `18h`
- margin: about `1.67x` over the sample-throughput projection

Stop condition:
- stop naturally when the one configured run completes `4200` clean chunks and writes `final_summary.json`
- stop early on runner failure
- if the first checkpoint projection exceeds the `18h` budget, rescope before launching another same-family cell

Output and log targets:
- output directory: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage2_fwd_full_len2_14_pc_a`
- runner tee log: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/logs/stage2_fwd_full_len2_14_pc_a.log`

Preflight:
- `python -m pytest tests/tools/test_phaseB_runeberg_nose_damage_ladder_v1.py`
- result: `33 passed`
