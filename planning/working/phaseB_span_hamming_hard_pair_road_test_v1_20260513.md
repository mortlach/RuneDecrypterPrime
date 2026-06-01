# PhaseB Span-Hamming Hard-Pair Road Test v1 - 2026-05-13

Purpose:

- run the hard-pair rescue/break test requested after road-test v1
- use historical no-WLI misrank/rescore pairs where both candidate token streams
  can be resolved
- keep the work report-only; no production scorer changes

Inputs:

- pair rows:
  - `planning/projects/no_wli/40_review_summaries/no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/historical_pairwise_rescore/historical_pairwise_rescore_pairs.csv`
- token source:
  - `planning/projects/no_wli/40_review_summaries/no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/historical_partial_texts/unique_partial_text_rows.csv`
- active calibration:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`

Implementation:

- script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_span_hamming_hard_pair_road_test_v1.py`
- output folder:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_hard_pair_road_test_v1_review_pack_2026-05-13.zip`

Run result:

- historical pair rows:
  - `2594`
- current-scorer misrank rows:
  - `602`
- resolved token hashes:
  - `604 / 604`
- candidates scored once:
  - `604`
- chunks scored:
  - `1208`
- feature comparison rows:
  - `1420608`
- elapsed:
  - about `473s`
- review zip:
  - about `66.3 MB`
- zip integrity:
  - passed

Hard-pair rescue/break result:

- Panel A, medium lengths `5..9`:
  - truth-better preference: `1904 / 2594` (`0.734`)
  - current-scorer misranks rescued by always-preferring Panel A: `274`
  - current-correct pairs broken by always-preferring Panel A: `362`
  - net rescue minus break: `-88`
- Panel B, longer lengths `10..14`:
  - truth-better preference: `1326 / 2594` (`0.511`)
  - rescues: `168`
  - breaks: `828`
  - net: `-660`
- Panel D, strict precision:
  - truth-better preference: `1684 / 2594` (`0.649`)
  - rescues: `168`
  - breaks: `476`
  - net: `-308`

Margin-sweep result:

- Panel A best net in the tested margin sweep:
  - margin threshold `0.4`
  - rescues `4`
  - breaks `0`
  - overrides `788`
  - net `+4`
- Panel B best net:
  - `0`
- Panel D best net:
  - `0`

Interpretation:

- The hard-pair test confirms Panel A is directionally correlated with truth:
  - it prefers the truth-better candidate in about `73%` of historical pairs.
- But Panel A is not a safe standalone rescue/break policy:
  - naive always-override has more breaks than rescues
  - margin-threshold/abstain policies do not produce a useful rescue rate
- Panel B is not useful as a hard-pair chooser under the current Stage 3 calibration.
- Panel D is useful as precision/support evidence, but also not safe as a standalone
  chooser.
- Historical bad/weak candidates often have high local span-Hamming evidence, which
  strengthens the conclusion that the next layer must test order/phrase coherence.

Current conclusion:

- Span-Hamming remains useful local damaged-word evidence.
- It should not be used by itself to override current scorer rankings.
- The next report-only step should combine:
  - Panel A / Panel D local evidence
  - order, phrase, and ngram coherence evidence
  - explicit rescue/break accounting on the same hard-pair dataset

Scorer policy:

- no production scorer weights changed
- no scorer defaults changed
- no ranking policy changed
