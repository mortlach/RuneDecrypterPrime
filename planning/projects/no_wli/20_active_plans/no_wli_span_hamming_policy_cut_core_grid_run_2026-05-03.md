# No-WLI Span-Hamming Policy-Cut Core Grid Run - 2026-05-03

## Status

Launched in a separate PowerShell window, then stopped for strategy review.
Not complete. No summary JSON/readout was written.

Initial log confirmation:

- token hashes: `604`
- pair rows: `2594`
- configs: `110`
- total candidate scores: `66440`
- early progress: `1000 / 66440`
- early ETA: about `33` minutes while still in the cheaper `raw_selected`
  early templates
- summary JSON: not written yet

Later user-raised concern:

- ETA was increasing as the run moved from `hd1` into `hd2`.
- This is expected for mixed-cost configs, but it also shows that a monolithic
  averaged ETA is misleading.
- Run stopped before completion so we can tighten the scan around the real
  problem before spending more runtime.

## Reason For Replacing The Previous Full Policy-Cut Run

The stopped `span_hamming_full_policy_cut_calibration_v1` run expanded to
`243` configs and `146772` candidate scores, but it included known duplicate
work:

- `normal_selected` loads identically to `raw_selected`.
- `strict_all`, `normal_all`, and `broad_all` load identically to `raw_all`
  because `require_selected=False` ignores the selected column.
- `hd3` is much slower than `hd2` and should be treated as a separate slow-path
  follow-up.
- exact `hd0` cap variants were identical in the completed S1f raw scan, so the
  core grid keeps only cap `256` for exact `hd0`.

The stopped run wrote no summary JSON/readout, so it is not complete evidence.
The final log progress before stop was `6000 / 146772`.

## Core Grid Included Values

Dictionaries run:

- `raw_selected`
- `raw_all`
- `strict_selected`
- `broad_selected`
- `research_selected`

Dictionary aliases not run in this core pass:

- `normal_selected`: alias of `raw_selected`
- `strict_all`, `normal_all`, `broad_all`: aliases of `raw_all`

Span templates and caps:

- `len1_14_hd0_exact`: cap `256`
- `len1_14_hd1`: caps `256`, `512`, `1024`
- `len1_14_hd2`: caps `256`, `512`, `1024`
- `len3_14_hd2_s1b_shape`: caps `256`, `512`, `1024`
- `len5_14_hd2_longer`: caps `256`, `512`, `1024`
- `len8_14_hd2_long_signal`: caps `256`, `512`, `1024`
- `len10_14_hd2_very_long_signal`: caps `256`, `512`, `1024`
- `len1_4_hd2_short_noise`: caps `256`, `512`, `1024`

Counts:

- configs: `110`
- token hashes per config: `604`
- candidate scores: `66440`

## Not Included

- `hd3`: split to a separate slow-path decision after this core grid.
- cap `2048`: not included.
- RTL: not included.
- word-ngram downstream sweep: not included.
- every possible `(len_min, len_max)` pair: not included.

## Runtime Budget

Completed references:

- Focused 5-config policy comparison: `4.55` minutes.
- Previous raw/all S1f run: `54` configs in `37.0` minutes.
- Stopped duplicate full run reached `6000 / 146772` before being halted,
  and ETA had climbed to about `185` minutes inside the slow `hd3` section.

Core-grid intended wallclock budget: `2 hours`.

Stop condition:

- Stop and rescope if projected ETA exceeds `2.5 hours`.
- Stop and inspect if parity failures or missing dictionary paths appear.

## Outputs

- Runner: `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_span_hamming_policy_cut_core_grid_v1.py`
- Output directory: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_policy_cut_core_grid_v1`
- Log file: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_policy_cut_core_grid_v1/span_hamming_policy_cut_core_grid_v1.log`
