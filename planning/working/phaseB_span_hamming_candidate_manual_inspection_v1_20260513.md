# PhaseB Span-Hamming Candidate Manual Inspection v1 - 2026-05-13

Purpose:

- build a human-readable inspection pack for the real no-WLI candidate texts used
  in the hard-pair road test
- inspect bad candidates that span-Hamming likes, good supported candidates,
  rescues, breaks, and high-current-score bad cases
- report-only; no production scorer changes

Implementation:

- script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_span_hamming_candidate_manual_inspection_v1.py`
- output folder:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_candidate_manual_inspection_v1_review_pack_2026-05-13.zip`

Inputs:

- hard-pair road-test output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`
- token/text source:
  - `planning/projects/no_wli/40_review_summaries/no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/historical_partial_texts/unique_partial_text_rows.csv`
- historical pair metadata:
  - `planning/projects/no_wli/40_review_summaries/no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/historical_pairwise_rescore/historical_pairwise_rescore_pairs.csv`

Outputs:

- `config.json`
- `input_manifest.json`
- `readout.md`
- `candidate_manual_inspection.csv`
- `pair_manual_inspection.csv`
- `top_panelA_false_positives.csv`
- `top_panelA_true_positives.csv`
- `panelA_rescues.csv`
- `panelA_breaks.csv`
- `high_current_score_bad_candidates.csv`
- `candidate_manual_inspection.md`
- `pair_manual_inspection.md`
- `candidate_full_texts.jsonl.gz`

Run result:

- candidates with readable token/latin snippets:
  - `604 / 604`
- pairs with both candidate texts resolved:
  - `2594 / 2594`
- label counts:
  - `known_bad`: `33`
  - `known_good`: `47`
  - `likely_bad`: `90`
  - `likely_good`: `269`
  - `unknown`: `165`
- snippet policy:
  - first `250` tokens
  - middle `250` tokens
  - last `250` tokens
- full text sidecar:
  - `candidate_full_texts.jsonl.gz`
- zip integrity:
  - passed
- missing/incomplete sources:
  - none observed

Highest Panel A known/likely bad examples:

- `hist_text_53762f26f296b010bdb8fb6f`
  - label `known_bad`, Panel A `2.32353354606`, truth `0.041`, current `0.184461046208`
- `hist_text_039bb659d84282dc2df09377`
  - label `known_bad`, Panel A `2.31364281988`, truth `0.041`, current `0.222691790618`
- `hist_text_67fed75e05c7225c4957a116`
  - label `known_bad`, Panel A `2.31191441559`, truth `0.041`, current `0.223544661001`
- `hist_text_0531025eaa7d726b1f0fa6f6`
  - label `known_bad`, Panel A `2.30881246249`, truth `0.041`, current `0.222709293544`
- `hist_text_0e6076c495dd3fc8b867a720`
  - label `known_bad`, Panel A `2.30725726923`, truth `0.041`, current `0.222466646435`

Largest Panel A rescues:

- `a704860e4663b7e9bb97650a`
  - Panel A gap `0.4348291824`, truth better `0.455`, truth worse `0.335`
- `27bbc31318d7a881876d4f31`
  - Panel A gap `0.4348291824`, truth better `0.455`, truth worse `0.335`
- `aa276d8d44b03f2dd57e01bb`
  - Panel A gap `0.4348291824`, truth better `0.455`, truth worse `0.335`

Largest Panel A breaks:

- `06917810604f4512eed1b840`
  - Panel A gap `-0.31317518882`, truth better `0.466`, truth worse `0.337`
- `dee7d3e772b14e218eac8067`
  - Panel A gap `-0.31317518882`, truth better `0.466`, truth worse `0.337`
- `b745e971df8b14e16b0fb549`
  - Panel A gap `-0.30973857075`, truth better `0.466`, truth worse `0.337`

Automatic pattern clue:

- breaks mean truth-worse minus truth-better repeated-3gram rate:
  - `-0.00411873`
- rescues mean truth-worse minus truth-better repeated-3gram rate:
  - `-0.00351798`
- initial automatic repeated-3gram contrast alone does not explain the breaks.

Manual review flags:

- added blank columns:
  - `looks_like_local_words`
  - `looks_like_order_scrambled`
  - `looks_like_repetition`
  - `looks_like_short_word_overmatch`
  - `looks_like_periodic_or_lane_artifact`
  - `looks_like_partial_plaintext`
  - `label_maybe_wrong`
  - `manual_comment`

Scorer policy:

- no production scorer weights changed
- no scorer defaults changed
- no candidate ranking policy changed
- no calibration outputs changed
- Stage 4 run left untouched
