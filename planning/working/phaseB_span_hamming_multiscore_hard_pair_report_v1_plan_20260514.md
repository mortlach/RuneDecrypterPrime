# PhaseB Span-Hamming Multiscore Hard-Pair Report v1 - Planning Log - 2026-05-14

## What changed

Added an active plan for a report-only whole-ladder span-Hamming hard-pair report:

- `planning/projects/no_wli/20_active_plans/phaseB_span_hamming_multiscore_hard_pair_report_v1_plan_2026-05-14.md`

## Why it matters

Data-taking is paused, but the existing hard-pair candidate feature rows and
Stage 1+2 / Stage 3 / Stage 4 calibration summaries are enough to ask the next
report-only question:

```text
Can calibrated span-Hamming feature space improve on simple Panel A/B/D
hard-pair scores before adding phrase/order evidence?
```

## Evidence / linked files

Hard-pair source:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`

Observed important files:

- `candidate_feature_rows.csv.gz`
- `pairwise_road_test_summary.csv`
- `candidate_level_summary.csv`
- `candidate_chunk_manifest.csv`
- `candidate_manifest_resolved.csv`
- `hard_pair_manifest.csv`
- `readout.md`
- `config.json`

Calibration sources:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage1_stage2_fwd_full_len2_14_combined_v1`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb`

## Planning decisions

- Keep the work report-only.
- Reproduce the previous Panel A baseline first.
- Rematch hard-pair candidate feature rows to Stage 4 calibration where keys
  overlap.
- Use local-null evidence as the main positive target.
- Treat block-shuffle behavior as stress/warning diagnostics.
- Use labels for evaluation and transparent row selection only, not free-weight
  fitting.
- Use lengths `5..14` for initial score families because the existing hard-pair
  candidate feature rows cover that range.
- Treat lengths `2..4` as calibration-side diagnostics unless a later report-only
  candidate extraction is explicitly planned.

## Next step

Implement:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_span_hamming_multiscore_hard_pair_report_v1.py
```

with hardcoded constants and repo-root-relative path resolution.

Target output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1
```

## What did not change

- No new calibration/data-taking is authorized.
- No production scorer weights/defaults/ranking policy are changed.
- FWD and REV remain separate.
- Stage 4 is not modified.

## Implementation update

Implemented and ran:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_span_hamming_multiscore_hard_pair_report_v1.py
```

Output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1
```

Review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_multiscore_hard_pair_report_v1_review_pack_2026-05-14.zip
```

Run summary:

- candidates: `604`
- hard pairs: `2594`
- feature keys: `196`
- row-efficacy rows: `1960`
- elapsed: about `78s`
- Panel A baseline reproduced:
  - truth preference `1904 / 2594` (`0.734`)
  - rescues `274`
  - breaks `362`
  - net `-88`

Initial readout:

- `S5_local_null_positive_selected` slightly improves broad truth preference over
  Panel A (`0.739` vs `0.734`) and improves net rescue/break (`-74` vs `-88`),
  but remains break-heavy as a broad override.
- positive-net behavior appears only in conservative/support-policy simulations,
  not in a broad span-Hamming-only override.
- this supports the prior interpretation: span-Hamming is useful local evidence,
  but order/phrase/ngram evidence is still needed before scorer-policy changes.
