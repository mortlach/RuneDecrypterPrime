# No-WLI Span-Hamming Full Policy-Cut Calibration Run - 2026-05-03

## Purpose

Run the full S1f span-Hamming calibration grid after restoring the policy-cut
dictionary assets:

- `strict`
- `normal`
- `broad`
- `research`

This is report-only. It does not change runtime scorer or solver behaviour.

## Inputs

- Pair rows: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv`
- Partial text rows: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/historical_partial_text_review_v1/unique_partial_text_rows.csv`
- Policy assets: `assets/hamming_dictionary_policies/*/hamming_raw_1g`
- Runner: `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_span_hamming_full_policy_cut_calibration_v1.py`

## Runtime Sizing

Completed same-family references:

- Previous S1f run: `54` runnable configs, `604` token hashes, `37.0` minutes.
- Focused policy-cut comparison: `5` configs, `604` token hashes, `4.55` minutes.

Restored policy assets make the full grid `243` requested configs. Linear
projection from the previous S1f run is about `167` minutes. Linear projection
from the focused policy-cut comparison is about `221` minutes. Intended budget:
`4 hours`.

## Stop Conditions

- Normal stop: the run completes and writes the summary JSON/readout.
- Early stop for manual intervention: after the first several progress lines,
  if ETA projects beyond `4 hours` by a large margin, stop and split by
  dictionary family.
- Early stop for manual intervention: if the log shows parity failures or
  missing policy dictionaries, stop and inspect before continuing.

## Outputs

- Output directory: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_full_policy_cut_calibration_v1`
- Log file: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_full_policy_cut_calibration_v1/span_hamming_full_policy_cut_calibration_v1.log`

## Status

- Launched in a separate PowerShell window.
- Not complete yet.
- Last checked progress: `5700 / 146772` candidate scores.
- Last checked ETA: about `148` minutes while still early in the `raw_selected` section.
- No summary JSON/readout has been written yet.

