# PhaseB Span-Hamming Road-Test v1 Review and Next Actions - 2026-05-13

Status:

- Stage 4 calibration is running on PCB.
- Do not start another calibration stage until Stage 4 finishes and is reviewed.
- Road-test v1 has been built and run:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_span_hamming_real_candidate_road_test_v1.py`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_real_candidate_road_test_v1/`
- Road-test review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_real_candidate_road_test_v1_review_pack_2026-05-13.zip`

Working interpretation:

- Road-test v1 is a success.
- It does not show that span-Hamming is sufficient by itself.
- It shows that span-Hamming is a useful local damaged-word evidence layer:
  - it separates good from bad candidates on average
  - it does not reject all high-scoring bad/gibberish candidates

Candidate coverage:

- candidates scored: `246`
- chunks scored: `492`
- feature comparison rows: `578592`

Label counts:

- `known_bad`: `38`
- `likely_bad`: `35`
- `known_good`: `24`
- `likely_good`: `35`
- `unknown`: `114`

Main Panel A result:

- Panel A is the medium-span local evidence panel:
  - lengths `5..9`
  - local span-Hamming evidence
- candidate means:
  - `known_good`: `3.665`
  - `likely_good`: `2.764`
  - `known_bad`: `0.591`
  - `likely_bad`: `0.942`
- at threshold `0.5`, known/likely bad pass fraction is `0.616`
- interpretation:
  - high Panel A means local damaged-word evidence exists
  - low Panel A means weak local plaintext evidence / likely poor candidate
  - high Panel A does not mean definitely good plaintext

Threshold guidance:

- `Panel A > 0.5`:
  - broad local-word evidence, permissive
- `Panel A > 1.0` or `1.5`:
  - stronger support, fewer known-bad candidates pass
- `Panel A > 2.0`:
  - strong support, but still not proof of correct plaintext
- Do not hard-code these as production thresholds yet.
- Treat them as review guidance only.

Panel B and Panel D:

- Panel B:
  - lengths `10..14`, longer-span evidence
  - v1 means:
    - `known_good`: `0.527`
    - `known_bad`: `-0.003`
    - `likely_bad`: `0.011`
  - currently weaker; refresh after Stage 4 adds more long-span calibration.
- Panel D:
  - strict precision evidence
  - v1 means:
    - `known_good`: `1.911`
    - `known_bad`: `0.302`
    - `likely_bad`: `0.470`
  - useful as a precision/support panel; keep it.

Pairwise status:

- constructed target-vs-final_best checks:
  - `20 / 20` Panel A preferred the known-good target
- this is a good sanity check.
- it is not yet the hard pairwise result needed next.
- next stronger test:
  - historical misrank pairs where both real candidate token streams are available.

Main caveat:

- Road-test v1 uses real candidate outputs.
- Available labelled pair artifacts were incomplete.
- Historical pairwise scorer rows were found, but the original token artifacts were
  not fully present locally.
- Next road test should target the real historical misrank corpus with actual
  candidate token streams.

Interpretation of bad candidates passing:

- Some known-bad candidates score high on Panel A.
- This is not a failure of the experiment.
- It means those candidates contain local word-like fragments.
- Span-Hamming tests local word evidence; it does not test global order or phrase
  coherence.
- This matches the block-shuffle lesson:
  - a text can preserve local word-like fragments while being wrong globally.
- Therefore an order/phrase/ngram evidence layer is still needed.

Scorer policy:

- Road-test v1 is report-only.
- Do not change production scorer weights, scorer defaults, or ranking policy based
  on this alone.
- Next scoring work remains report-only until hard-pair rescue/break evidence exists.

Next actions:

1. Let Stage 4 finish.
   - Review `run_state.json`, `final_summary.json`, `readout.md`,
     `timing_checkpoints.csv`, `final_feature_summary.csv`,
     damaged-vs-null summaries, convergence summaries, `feature_histograms.csv.gz`,
     and `feature_quantiles.csv.gz`.
2. Refresh road-test after Stage 4.
   - Merge Stage 4 into the calibration bundle.
   - Rerun or refresh road-test panel tables.
   - Key question: does Panel B, lengths `10..14`, become more useful after Stage 4?
3. Build the hard-pair road test.
   - Locate or reconstruct historical no-WLI candidate token streams for the
     misranked pair dataset.
   - Required manifest shape:
     - `pair_id`
     - `candidate_a_id`
     - `candidate_b_id`
     - `current_scorer_preferred`
     - `known_better_candidate`
     - `candidate_a_token_path`
     - `candidate_b_token_path`
     - `current_score_a`
     - `current_score_b`
     - `truth_or_label_metadata`
   - Required output:
     - `pair_id`
     - `current_scorer_correct`
     - `span_hamming_panel_preferred`
     - `span_hamming_rescues_current_misrank`
     - `span_hamming_breaks_current_correct`
     - `panel_scores_a`
     - `panel_scores_b`
4. Keep Panel A as local evidence, not final score.
   - Panel A high + order evidence high: stronger candidate.
   - Panel A high + order evidence low: likely local-gibberish / wrong-order candidate.
   - Panel A low: weak local plaintext evidence.
5. Begin planning order/phrase/ngram evidence.
   - Keep report-only at first.
   - Goal: separate local word-like material from coherent language order.

Suggested next review pack contents:

- `config.json`
- `run_manifest.json`
- `run_state.json`
- `final_summary.json`
- `readout.md`
- `timing_checkpoints.csv`
- `dictionary_hash_manifest.csv`
- `candidate_manifest_resolved.csv`
- `candidate_chunk_manifest.csv`
- `candidate_panel_summary.csv`
- `candidate_level_summary.csv`
- `pairwise_road_test_summary.csv`
- `bad_candidate_separation_summary.csv`
- `top_supported_candidates.csv`
- `top_warning_candidates.csv`

Optional compact files:

- `clean_chunk_manifest.csv`
- `damage_fraction_summary.csv`
- `hard_pair_manifest.csv`

No raw `feature_rows.csv` is needed unless specifically requested.

Bottom line:

- Span-Hamming is real and useful.
- Panel A, lengths `5..9`, is the strongest local evidence.
- Panel D strict evidence adds useful precision.
- Panel B longer evidence is currently weaker but should be refreshed after Stage 4.
- Span-Hamming alone does not solve high-scoring gibberish.
- The next critical test is hard-pair rescue/break analysis using real candidate
  token streams.

Hard-pair update:

- completed:
  - `planning/working/phaseB_span_hamming_hard_pair_road_test_v1_20260513.md`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_hard_pair_road_test_v1_review_pack_2026-05-13.zip`
- historical pair rows:
  - `2594`
- token streams resolved:
  - `604 / 604`
- current-scorer misrank rows:
  - `602`
- Panel A hard-pair result:
  - truth-better preference `1904 / 2594` (`0.734`)
  - rescues `274`
  - breaks `362`
  - net `-88`
- Panel A margin-sweep best net:
  - threshold `0.4`
  - rescues `4`
  - breaks `0`
  - net `+4`
- updated conclusion:
  - Panel A is directionally useful but not a safe standalone override rule
  - Panel D is useful support/precision evidence but not a standalone chooser
  - next report-only scorer work should combine local span-Hamming evidence with
    order/phrase/ngram coherence and keep rescue/break accounting on the hard-pair
    dataset

Data-taking pause update:

- as of `2026-05-14`, new no-WLI calibration/data-taking is paused
- pause note:
  - `planning/working/no_wli_data_taking_pause_20260514.md`
- handoff note:
  - `planning/working/no_wli_current_status_handoff_data_pause_20260514.md`
- do not launch Stage 5 calibration, PCA data collection, or another PCB
  continuation by default
- resume data-taking only if a later report-only test or reviewer question identifies
  a concrete missing calibration/data slice
- while paused, prioritize:
  - merge/refresh Stage 1-4 calibration for report-only road tests
  - refresh Panel B with Stage 4 included
  - develop order/phrase/ngram evidence on the hard-pair dataset
