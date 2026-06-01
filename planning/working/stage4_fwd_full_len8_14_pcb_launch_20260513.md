# stage4_fwd_full_len8_14_pcb launch note

Date: 2026-05-13

Script:
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_stage4_len8_14_pcb.py`

Run identity:
- run label: `stage4_fwd_full_len8_14_pcb`
- run mode: `stage4_fwd_full_len8_14_pcb`
- machine: `PCB only`
- chunk start: `22400`
- clean chunks: `12000`
- expected next chunk start: `34400`
- directions: `fwd`
- score region: `full`
- start shift: `0`
- active span lengths: `8..14`
- ladder profile: `v0_3_plus_long_relaxed_v2_len8_14`

Active HD rungs:
- length `8`: `0,1,2,3`
- length `9`: `0,1,2,3,4`
- length `10`: `0,1,2,3,4`
- length `11`: `0,1,2,3,4,5`
- length `12`: `0,1,2,3,4,5`
- length `13`: `0,1,2,3,4,5,6`
- length `14`: `0,1,2,3,4,5,6`

Expected size:
- samples: `444000`
- total active ladder rungs per dictionary cut: `40`
- dictionary cuts: `phaseA14_strict_selected`, `phaseA14_normal_selected`
- feature rows: `35520000`
- raw `feature_rows.csv`: `off`
- histograms: `on`
- quantiles: `on`
- convergence summaries: `on`
- damaged-vs-null summaries: `on`
- timing summaries: `on`

Retained runtime reference:
- same-machine same-family anchor:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb/final_summary.json`
- anchor elapsed: `85298.1381107s`
- anchor coverage: `10000` clean chunks, `370000` samples, `36260000` feature rows
- observed sample throughput: `4.337726569363257` samples/s
- observed feature-row throughput: `425.09720379759915` rows/s

Sizing:
- projected wallclock from feature-row throughput: about `23.21h`
- projected wallclock from sample throughput: about `28.43h`
- intended wallclock budget: `23-29h`
- note: feature-row throughput is the closest same-machine/same-run-family anchor;
  the first checkpoint should be reviewed before any later continuation is
  considered

Stop condition:
- stop naturally when the one configured run completes `12000` clean chunks and writes `final_summary.json`
- stop early on runner failure
- do not start another calibration continuation until this Stage 4 result is reviewed

Output and log targets:
- output directory: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb`
- runner tee log: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/logs/stage4_fwd_full_len8_14_pcb.log`
- PowerShell tee log: `output/logs/stage4_fwd_full_len8_14_pcb_run.log`
- launch script: `planning/projects/no_wli/60_launch_scripts/stage4_fwd_full_len8_14_pcb_launch_2026-05-13.ps1`

Preflight:
- `python -m pytest tests/tools/test_phaseB_runeberg_nose_damage_ladder_v1.py`
- result: `33 passed`
- exact config assertion: passed
- verified output directory did not exist before launch
- verified output/log parents resolve under repo root and exist

Launch:
- launched in a separate PowerShell window from:
  - `planning/projects/no_wli/60_launch_scripts/stage4_fwd_full_len8_14_pcb_launch_2026-05-13.ps1`
- launcher PowerShell process id observed by parent terminal:
  - `13124`
- startup log confirmed:
  - `estimated_samples=444000`
  - `estimated_feature_rows=35520000`
  - output shape has `40` ladder rows per dictionary and `2` dictionary cuts

First checkpoint:
- checkpoint index: `1`
- samples: `500 / 444000`
- feature rows: `40000 / 35520000`
- chunks observed so far: `14`
- elapsed: `93.219729s`
- samples/sec: `5.36367144332`
- feature rows/sec: `429.093715465`
- median remaining estimate: `82685.899889s`
- projected total from first checkpoint: about `22.99h`
- raw `feature_rows.csv` absent at checkpoint
- decision:
  - continue; first checkpoint is within the feature-row-based `23-24h`
    expectation and inside the retained-evidence budget

Road-test build checkpoint:
- checkpoint index: `12`
- samples: `6000 / 444000`
- feature rows: `480000 / 35520000`
- elapsed: `1093.9s`
- median remaining estimate: `74051.7s`
- raw `feature_rows.csv`: still absent
- decision:
  - continue; run remains healthy and no later calibration continuation should be
    launched before this Stage 4 result is reviewed

Road-test review note checkpoint:
- checkpoint index: `40`
- samples: `20000 / 444000`
- feature rows: `1600000 / 35520000`
- elapsed: `3279.4s`
- median remaining estimate: `71402.0s`
- status:
  - still running in the separate PowerShell window
  - do not start another calibration stage until Stage 4 finishes and is reviewed

Hard-pair road-test closeout checkpoint:
- checkpoint index: `54`
- samples: `27000 / 444000`
- feature rows: `2160000 / 35520000`
- elapsed: `4517.6s`
- median remaining estimate: `69409.9s`
- status:
  - still running in the separate PowerShell window
  - no later calibration stage launched

Manual-inspection pack closeout checkpoint:
- checkpoint index: `623`
- samples: `311500 / 444000`
- feature rows: `24920000 / 35520000`
- elapsed: `48813.5s`
- median remaining estimate: `20800.2s`
- status:
  - still running in the separate PowerShell window
  - no later calibration stage launched

Final closeout:
- status:
  - `complete`
- samples:
  - `444000 / 444000`
- feature rows:
  - `35520000 / 35520000`
- actual chunks used:
  - `12000`
- elapsed:
  - `69326.90s`
  - `19.26h`
- next chunk start:
  - `34400`
- raw `feature_rows.csv`:
  - absent as intended
- observed throughput:
  - `6.404` samples/s
  - `512.36` feature rows/s
- log scan:
  - no traceback, exception, warning, native command error, or unraisable-hook hits
- review pack:
  - `planning/projects/no_wli/40_review_summaries/stage4_fwd_full_len8_14_pcb_review_pack_2026-05-14.zip`
- conclusion:
  - Stage 4 strengthens lengths `8..11`, leaves lengths `13..14` weak, and should
    be merged/refreshed into road-test Panel B before any further calibration stage
