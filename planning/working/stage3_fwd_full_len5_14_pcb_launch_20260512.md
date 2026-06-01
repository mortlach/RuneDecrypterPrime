# stage3_fwd_full_len5_14_pcb launch note

Date: 2026-05-12

Script:
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_stage3_len5_14_pcb.py`

Run identity:
- run label: `stage3_fwd_full_len5_14_pcb`
- run mode: `stage3_fwd_full_len5_14_pcb`
- machine: `PCB only`
- chunk start: `12400`
- clean chunks: `10000`
- expected next chunk start: `22400`
- directions: `fwd`
- score region: `full`
- start shift: `0`
- active span lengths: `5..14`
- ladder profile: `v0_3_plus_long_relaxed_v2_len5_14`

Active HD rungs:
- length `5`: `0,1`
- length `6`: `0,1,2`
- length `7`: `0,1,2,3`
- length `8`: `0,1,2,3`
- length `9`: `0,1,2,3,4`
- length `10`: `0,1,2,3,4`
- length `11`: `0,1,2,3,4,5`
- length `12`: `0,1,2,3,4,5`
- length `13`: `0,1,2,3,4,5,6`
- length `14`: `0,1,2,3,4,5,6`

Expected size:
- samples: `370000`
- total active ladder rungs per dictionary cut: `49`
- dictionary cuts: `phaseA14_strict_selected`, `phaseA14_normal_selected`
- feature rows: `36260000`
- raw `feature_rows.csv`: `off`
- histograms: `on`
- quantiles: `on`
- convergence summaries: `on`
- damaged-vs-null summaries: `on`
- timing summaries: `on`

Retained runtime reference:
- same-machine anchor: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage2_fwd_full_len2_14_pc_b/final_summary.json`
- anchor elapsed: `66502.5843644s`
- anchor coverage: `7200` clean chunks, `266400` samples, `28771200` feature rows
- observed sample throughput: `4.005859359393687` samples/s
- observed feature-row throughput: `432.6328108145182` rows/s

Sizing:
- projected wallclock from feature-row throughput: about `23.28h`
- projected wallclock from sample throughput: about `25.66h`
- intended wallclock budget: `23-26h`

Stop condition:
- stop naturally when the one configured run completes `10000` clean chunks and writes `final_summary.json`
- stop early on runner failure
- do not start another stage until this Stage 3 result is reviewed

Output and log targets:
- output directory: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`
- runner tee log: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/logs/stage3_fwd_full_len5_14_pcb.log`
- PowerShell tee log: `output/logs/stage3_fwd_full_len5_14_pcb_run.log`
- launch script: `planning/projects/no_wli/60_launch_scripts/stage3_fwd_full_len5_14_pcb_launch_2026-05-12.ps1`

Preflight:
- `python -m pytest tests/tools/test_phaseB_runeberg_nose_damage_ladder_v1.py`
- result: `33 passed`
- exact config assertion: passed
- verified output directory did not exist before launch
- verified output/log parents resolve under repo root and exist

Launch:
- launched in a separate PowerShell window from:
  - `planning/projects/no_wli/60_launch_scripts/stage3_fwd_full_len5_14_pcb_launch_2026-05-12.ps1`
- launcher PowerShell process id observed by parent terminal:
  - `3592`
- startup log confirmed:
  - `estimated_samples=370000`
  - `estimated_feature_rows=36260000`
  - output shape has `49` ladder rows per dictionary and `2` dictionary cuts

First checkpoint:
- checkpoint index: `1`
- samples: `500 / 370000`
- feature rows: `49000 / 36260000`
- chunks observed so far: `14`
- elapsed: `126.731909s`
- samples/sec: `3.94533630499`
- feature rows/sec: `386.642957889`
- median remaining estimate: `93654.880455s`
- projected total from first checkpoint: about `26.05h`
- decision:
  - continue; first checkpoint is only slightly above the upper `26h` budget
    edge and still close enough to the corrected runtime estimate for this
    long run

Completion:
- status: `complete`
- finished at UTC: `2026-05-13T00:32:01.256983+00:00`
- elapsed: `85298.1381107s` (`23.69h`)
- samples: `370000`
- feature rows: `36260000`
- actual chunks: `10000`
- next chunk start: `22400`
- checkpoints: `741`
- observed sample throughput: `4.337726569363257` samples/s
- observed feature-row throughput: `425.09720379759915` rows/s

Save check:
- `final_summary.json`, `run_manifest.json`, `config.json`, and
  `run_state.json` parse with Python `json`
- `run_state.json` status is `complete`
- `timing_checkpoints.csv` has `742` lines
- `rolling_feature_summary.csv` has `742` lines
- `sample_rows.csv` has `370001` lines
- raw `feature_rows.csv` is absent, as configured
- log search found no `Traceback`, `Exception`, `Error`, `failed`,
  `NativeCommandError`, or `unraisablehook` text in saved tee logs

File sizes:
- `sample_rows.csv`: `104696402` bytes
- `convergence_summary.csv`: `198050314` bytes
- `damaged_vs_null_summary.csv`: `28664477` bytes
- `damaged_vs_null_by_view.csv.gz`: `4141830` bytes
- `final_feature_summary.csv`: `7542311` bytes
- `feature_histograms.csv.gz`: `658469` bytes
- `feature_quantiles.csv.gz`: `339853` bytes
- `timing_checkpoints.csv`: `127076` bytes
- `rolling_feature_summary.csv`: `145647` bytes

Review pack:
- folder:
  - `planning/projects/no_wli/40_review_summaries/stage3_fwd_full_len5_14_pcb_review_pack_2026-05-13/`
- zip:
  - `planning/projects/no_wli/40_review_summaries/stage3_fwd_full_len5_14_pcb_review_pack_2026-05-13.zip`
- source code intentionally excluded
- raw `sample_rows.csv`, raw `feature_rows.csv`, and full
  `convergence_summary.csv` intentionally excluded from the pack
