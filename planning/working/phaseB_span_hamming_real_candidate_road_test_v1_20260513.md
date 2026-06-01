# PhaseB Span-Hamming Real Candidate Road Test v1 - 2026-05-13

Purpose:

- report-only road test of calibrated span-Hamming evidence against real no-WLI
  solver/scorer candidates
- no production scorer weights changed

Implementation:

- script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_span_hamming_real_candidate_road_test_v1.py`
- output folder:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_real_candidate_road_test_v1`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_real_candidate_road_test_v1_review_pack_2026-05-13.zip`

Candidate source:

- fixed-panel external no-WLI review pack completed jobs:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/50_completed_job_runs`
- selected embedded FWD token arrays from:
  - `final_best_plaintext_idx`
  - `target_plaintext_idx`
  - capped `stage2_topk`
  - capped `stage3_topk`
  - capped `stage35_archive`

Calibration:

- active calibration:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`
- damage reference:
  - `word_local_substitution`, level `0.20`
- feature profile:
  - lengths `5..14`
  - `phaseA14_strict_selected`
  - `phaseA14_normal_selected`
  - `exact_count_norm`
  - `hd_le_count_norm`
- comparison nulls:
  - `uniform_random`
  - `global_frequency_random`
  - `within_chunk_shuffle`
  - `block_shuffle_10`
  - `block_shuffle_25`
  - `block_shuffle_50`

Run result:

- candidates scored:
  - `246`
- chunks scored:
  - `492`
- candidate feature comparison rows:
  - `578592`
- elapsed:
  - about `196s`
- review zip size:
  - about `27.6 MB`

Label counts:

- `known_bad`: `38`
- `likely_bad`: `35`
- `known_good`: `24`
- `likely_good`: `35`
- `unknown`: `114`

Key findings:

- Panel A, core medium lengths `5..9`, separates labelled good from labelled bad:
  - known-good mean `3.665`
  - likely-good mean `2.764`
  - known-bad mean `0.591`
  - likely-bad mean `0.942`
- However, Panel A alone is not sufficient:
  - known-bad pass fraction at threshold `0.5`: `0.474`
  - likely-bad pass fraction at threshold `0.5`: `0.771`
  - combined known/likely bad pass fraction reported in readout: `0.616`
- Panel B, longer lengths `10..14`, is weaker in this v1 candidate road test:
  - known-good mean `0.527`
  - likely-good mean `0.238`
  - known-bad mean `-0.003`
  - likely-bad mean `0.011`
- Panel D, strict precision rows, adds useful precision evidence:
  - known-good mean `1.911`
  - likely-good mean `1.429`
  - known-bad mean `0.302`
  - likely-bad mean `0.470`
- Panel C is absent by design in this v1 run because the active Stage 3 profile is
  lengths `5..14`; short lengths `2..4` remain diagnostic only for a later combined
  calibration run.
- Constructed target-vs-final_best pairwise readout:
  - `20` pairs
  - Panel A preferred the known-good target in all `20`
  - caveat: these are target controls, not independently current-scored candidate
    pairs.

Caveats:

- Historical pairwise scorer rows were found, but their original token artifacts were
  not fully present in local output, so v1 uses token-resolved candidates from the
  fixed-panel review pack and constructed target-vs-final_best pairs.
- Signed effects are oriented in the damaged-human direction and normalized by pooled
  damaged/null stddev. The first draft used damaged/null mean-gap normalization, but
  that made long-span rows unstable when calibration mean gaps were tiny.
- A bad candidate passing Panel A means local word-like evidence is present; it does
  not imply global order or phrase evidence is good.

Next review question:

- use this v1 pack to decide whether to token-resolve the historical pairwise
  candidate rows or wait for Stage 4 completion, merge Stage 4 into the calibration,
  and rerun the road test with refreshed longer-span panels.
