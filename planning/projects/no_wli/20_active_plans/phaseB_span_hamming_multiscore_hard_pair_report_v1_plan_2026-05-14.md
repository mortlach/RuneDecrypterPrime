# PhaseB Span-Hamming Multiscore Hard-Pair Report v1 Plan - 2026-05-14

Status: closed
Work status: implemented_report_run_closed
Project: no_wli
Owner: agent
Last updated: 2026-05-14
Successor plans:
- planning/projects/no_wli/20_active_plans/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_plan_2026-05-14.md
- planning/projects/no_wli/20_active_plans/phaseB_filtered_ngram_hard_pair_report_v1_plan_2026-05-14.md
Source-of-truth parents:
- planning/working/no_wli_data_taking_pause_20260514.md
- planning/working/no_wli_current_status_handoff_data_pause_20260514.md
- planning/working/phaseB_span_hamming_road_test_v1_review_next_actions_20260513.md
- output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1/readout.md

## Purpose

Build a report-only analysis that asks whether the whole calibrated
span-Hamming ladder can distinguish truth-better candidates from truth-worse
candidates in the historical hard-pair set better than the simple Panel A/B/D
road-test summaries.

This is not a production scorer change.
This is not a new calibration run.
This is not a new data-taking run.

The core question is:

```text
Can calibrated span-Hamming feature space help distinguish truth-better
candidates from truth-worse candidates in the historical hard-pair set?
```

## Pause Boundary

The data-taking pause remains in force.

Allowed:

- load existing hard-pair candidate feature rows
- load existing Stage 1+2, Stage 3, and Stage 4 calibration summaries
- rematch candidate rows to calibration summaries
- generate report CSVs, manifests, readouts, and plots from existing data
- run a bounded report-only script if it reads existing artifacts only

Not allowed in this plan:

- launch Stage 5 calibration
- start PCA data collection
- start another PCB continuation
- change production scorer weights, scorer defaults, or ranking policy
- use REV data in FWD calibration
- use candidate labels to fit many free production-like weights

## Local Input Check - 2026-05-14

Hard-pair source exists:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`

Observed hard-pair files:

- `candidate_level_summary.csv`
- `pairwise_road_test_summary.csv`
- `candidate_feature_rows.csv.gz`
- `candidate_chunk_manifest.csv`
- `candidate_manifest_resolved.csv`
- `hard_pair_manifest.csv`
- `readout.md`
- `config.json`

Observed candidate feature-row header includes:

```text
candidate_id,candidate_chunk_id,candidate_kind,candidate_rank,label,
label_confidence,source_run_id,source_file,current_score,current_score_name,
truth_match_ratio,chunk_index,chunk_token_count,chunk_status,direction,
score_region,start_shift,dictionary_cut,ladder_profile,span_length,hd,
feature_name,candidate_value,comparison_null_model,comparison_null_class,
calibration_damage_model,calibration_damage_level,damaged_mean,
damaged_stddev,null_mean,null_stddev,damaged_percentile,
comparison_null_percentile,signed_effect_vs_comparison_null,
signed_effect_vs_local_null,signed_effect_vs_block_shuffle,
calibration_n_chunks,calibration_n_samples,calibration_cohen_d,panels
```

Observed pairwise header includes:

```text
pair_id,candidate_a_id,candidate_b_id,current_scorer_correct,
span_hamming_panel_preferred,span_hamming_rescues_current_misrank,
span_hamming_breaks_current_correct,panel_scores_a,panel_scores_b,
current_scorer_preferred,known_better_candidate,winner_truth_match,
challenger_truth_match,truth_gap,winner_current_score,challenger_current_score,
current_score_margin
```

Existing hard-pair feature rows were generated from:

- active calibration: `stage3_fwd_full_len5_14_pcb`
- dictionary cuts: `phaseA14_strict_selected`, `phaseA14_normal_selected`
- lengths: `5..14`
- direction: `fwd`
- score region: `full`
- start shift: `0`
- pairs loaded: `2594`
- token hashes scored: `604`

Calibration sources available:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage1_stage2_fwd_full_len2_14_combined_v1`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb`

Stage 3 and Stage 4 include full calibration summaries such as:

- `final_feature_summary.csv`
- `damaged_vs_null_by_view.csv.gz`
- `damaged_vs_null_summary.csv`
- `feature_histograms.csv.gz`
- `feature_quantiles.csv.gz`
- `convergence_summary.csv`
- `dictionary_hash_manifest.csv`
- `final_summary.json`
- `readout.md`

Stage 1+2 combined currently has compact combined files, not the same full file
shape as Stage 3/4:

- `combined_damaged_vs_null_by_view.csv.gz`
- `combined_length_update.csv`
- `combined_readout.md`
- `combined_run_check.json`
- `combined_top_by_length.csv`

## Implementation Questions Answered For v1

1. Candidate feature rows are available, not just panel summaries. They cover the
   hard-pair set for the prior v1 feature extraction shape.
2. The candidate feature rows carry Stage 3 calibration columns, but Stage 4 can
   be included now by rematching candidate feature values to Stage 4 calibration
   summaries for overlapping row keys.
3. v1 should do both: reproduce the previous Panel A baseline first, then report
   the Stage 4-refreshed/merged calibration interpretation for overlapping rows.
4. Current scorer margins are available in `pairwise_road_test_summary.csv` as
   `current_score_margin`; candidate current scores are available at candidate
   level and pairwise winner/challenger level.
5. Truth-better labels appear unambiguous for the existing pair rows via
   `known_better_candidate`; the implementation should alias this to
   `truth_better_candidate_id` and derive the other side as truth-worse where
   both candidate ids are present.
6. Score families should not use labels to fit many free weights in v1. Labels are
   for row-efficacy reporting, transparent selected-row filters, and evaluation.
7. A development/holdout split can be attempted by `source_run_id` or pair source
   family if the distribution is adequate. If not adequate, the readout should say
   v1 is an exploratory full-set report.
8. Exact candidate texts are not needed for this report. Text inspection remains a
   follow-up using the manual inspection pack.
9. Lengths `2..4` should be included in calibration-side diagnostics where
   available, but the existing hard-pair candidate rows only cover `5..14`.
   They should not be part of initial score families unless a later report-only
   candidate feature extraction is explicitly planned.
10. Block-shuffle comparisons should be warning/stress diagnostics in v1, not the
    main positive target. Main positive evidence should use local nulls.

## Required Calibration Matching Keys

Every scored row must validate and join by:

```text
direction
score_region
start_shift
dictionary_cut
span_length
hd
feature_name
```

Calibration references also require:

```text
damage_model
damage_level
null_model
```

The primary expected run shape is:

```text
direction = fwd
score_region = full
start_shift = 0
```

Rows outside that shape should be reported, not silently pooled.

## Null Handling

Do not pool all nulls blindly.

Local nulls:

- `uniform_random`
- `global_frequency_random`
- `within_chunk_shuffle`

Block-shuffle controls:

- `block_shuffle_10`
- `block_shuffle_25`
- `block_shuffle_50`

Main score evidence should be judged against local nulls. Block-shuffle behavior
should be reported as a stress-control/warning dimension because block shuffles
preserve local fragments and are not expected to be rejected reliably by
span-Hamming alone.

## Calibration References To Test

Required single references:

- `word_local_substitution`, damage level `0.20`
- `word_local_substitution`, damage level `0.40`
- `independent_substitution`, damage level `0.40`
- `frequency_matched_global`, damage level `0.40`
- `frequency_matched_book`, damage level `0.40`
- `burst_substitution`, damage level `0.40`
- `lane_period_substitution`, damage level `0.40`

Optional pooled references:

- all damage models at `0.40`
- all damage models across `0.20..0.60`
- `word_local_substitution` across `0.20..0.60`

Pooled references must be labelled and compared against single-reference results
before any interpretation.

## Individual Row Efficacy

Create `row_efficacy_report.csv` with one row per candidate feature family and
calibration reference, for example:

```text
dictionary_cut = phaseA14_normal_selected
span_length = 6
hd = 2
feature_name = exact_count_norm
calibration_reference = word_local_substitution_0.20_vs_local_null
```

Candidate-level statistics:

- known-good mean
- known-bad mean
- likely-good mean
- likely-bad mean
- unknown mean
- good-minus-bad difference
- good-vs-bad Cohen d

Pairwise statistics:

- truth-better preference count/rate
- binomial 95% CI
- mean and median truth gap
- gap q05/q25/q75/q95
- rescues
- breaks
- net rescues

Current-scorer relation:

- correlation with current score
- correlation with current-score margin
- truth-gap mean when current scorer is correct
- truth-gap mean when current scorer is wrong
- truth-preference rate when current scorer is correct
- truth-preference rate when current scorer is wrong

Calibration metadata:

- damaged mean
- local-null mean
- block-shuffle mean
- local-null effect
- block-shuffle effect
- calibration chunk/sample counts
- convergence status if available

Provisional status vocabulary:

- `core_candidate`
- `supporting_candidate`
- `precision_candidate`
- `diagnostic_only`
- `risky_breaks_too_many`
- `weak`
- `needs_more_data`
- `do_not_use`

The status is a guide for report interpretation, not a production rule.

## Score Families

All score families must be transparent and saved in
`score_definition_manifest.json`.

S0 - Existing Panel A baseline:

- reproduce the existing Panel A result where possible
- lengths `5..9`
- normal dictionary emphasis
- normalized features

S1 - Normal-only per-length capped `5..9`:

- select useful normal-dictionary rows per length
- cap each length contribution
- average over lengths

S2 - Normal-only per-length capped `5..14`:

- same as S1, extended to longer lengths
- tests whether long spans add useful evidence

S3 - Strict-only score:

- use `phaseA14_strict_selected`
- test `5..9` and `5..14`

S4 - Normal plus strict precision support:

- normal per-length capped `5..9`
- add strict precision support term

S5 - Local-null positive selected rows:

- positive damaged-vs-local-null effect
- stable/converged where metadata exists
- not strongly negative against block-shuffle unless labelled as allowed
- reasonable pairwise truth preference

S6 - Per-HD band score:

- low HD: `0..1`
- middle HD: `2..3`
- relaxed HD: `4..6` where available

S7 - Current-score uncertainty support:

- use span-Hamming only when absolute current-score margin is below a threshold
- keep current scorer preference outside the uncertainty band

S8 - Anti-break conservative score:

- only prefer the span-Hamming candidate when span-Hamming margin exceeds a high
  threshold
- identify low-break rescue coverage

## Required Reports

Per-length and per-HD outputs:

- `length_hd_efficacy_report.csv`
- `length_summary.csv`
- `hd_summary.csv`
- `dictionary_cut_summary.csv`
- `feature_name_summary.csv`

Score-level outputs:

- `score_family_pairwise_summary.csv`
- `score_family_margin_sweep.csv`
- `pairwise_score_gaps.csv.gz`
- `top_rescues_by_score.csv`
- `top_breaks_by_score.csv`

Candidate-level outputs:

- `candidate_multiscore_summary.csv`
- `top_supported_candidates.csv`
- `top_warning_candidates.csv`
- `known_bad_high_span_hamming.csv`
- `known_good_low_span_hamming.csv`
- `unknown_high_span_hamming.csv`

Manifests/readout:

- `config.json`
- `input_manifest.json`
- `calibration_manifest.json`
- `score_definition_manifest.json`
- `readout.md`

Optional plots, generated only from report CSVs:

- `plots/score_family_truth_preference_bar.png`
- `plots/score_family_rescue_break_bar.png`
- `plots/panel_gap_histograms.png`
- `plots/score_margin_sweep.png`
- `plots/length_hd_heatmap_truth_preference.png`
- `plots/length_hd_heatmap_net_rescue.png`
- `plots/score_gap_vs_current_margin_scatter.png`
- `plots/candidate_score_distribution_by_label.png`

No AI-generated visuals.

## Output Folder

Write report outputs to:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1
```

## Readout Questions

`readout.md` must answer:

- Which score family performs best?
- Does any span-Hamming-only score beat Panel A?
- Does any score give positive net rescues at useful coverage?
- Which lengths help?
- Which HD rungs help?
- Does strict help?
- Does normal dominate?
- Do long lengths `10..14` add useful independent signal?
- Are failures mostly high local-word evidence but likely poor order/coherence?
- How correlated are the best span-Hamming scores with the current scorer?
- Is span-Hamming useful as an override, support signal, or diagnostic only?

## Implementation Shape

Create a report-only script with hardcoded configuration constants. Do not add CLI
arguments.

Recommended script path:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_span_hamming_multiscore_hard_pair_report_v1.py
```

Implementation requirements:

- resolve repo root from the script location
- use repo-relative output paths in config, manifests, readouts, and console logs
- validate all required inputs before scoring
- write missing-field and missing-calibration coverage into the readout
- write partial outputs where safe if optional calibration references are absent
- reproduce the existing Panel A hard-pair baseline before interpreting new scores
- keep FWD/REV separate
- avoid changing existing calibration or road-test outputs

## Runtime / Launch Guidance

This is expected to be a report-only file-processing job, not a multi-hour
calibration/data-taking run.

Before launch:

- verify all output parents resolve under the repo root
- estimate row counts from input files
- decide whether it can run in the interactive terminal

If implementation turns into a long investigation run, follow `AGENTS.md`:

- launch in a separate PowerShell window
- tee stdout/stderr to a repo-relative log file
- emit completed-versus-total work, elapsed time, and ETA
- define a stop condition before launch

## Success Criteria

The report succeeds if it gives a clear answer to:

```text
How much can span-Hamming contribute before adding phrase/order evidence?
```

Good possible outcome:

- a span-Hamming-only multi-score gives positive net rescues at useful coverage

Still useful outcome:

- span-Hamming-only scores are truth-correlated but not safe as overrides
- span-Hamming should be used as a support/diagnostic layer with order/ngram
  evidence

Either outcome is acceptable if the outputs are traceable and the readout is clear.

## Implementation Status - 2026-05-14

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

Run facts:

- candidates: `604`
- hard pairs: `2594`
- feature keys: `196`
- row-efficacy rows: `1960`
- elapsed: about `78s`
- baseline Panel A reproduced:
  - truth preference `1904 / 2594` (`0.734`)
  - rescues `274`
  - breaks `362`
  - net `-88`

Initial interpretation:

- `S5_local_null_positive_selected` slightly improves broad truth preference over
  Panel A (`0.739` vs `0.734`) and improves net rescue/break (`-74` vs `-88`),
  but remains break-heavy as a broad override.
- Positive-net behavior appears only in conservative/support-policy simulations,
  not in a broad span-Hamming-only override.
- This keeps the data-taking pause intact and points next toward
  phrase/order/ngram evidence.

## Closeout - 2026-05-14

This plan is closed as implemented.

The multiscore span-Hamming report established the carry-forward support
signals and showed that broad span-Hamming-only override remains break-heavy.
The useful outputs now serve as baselines/reference features for the filtered
n-gram hard-pair report:

- Panel A baseline
- `S5_local_null_positive_selected`
- `normal length 7 HD2 exact_count_norm`

No further span-Hamming calibration or production scorer change is authorized by
this plan.

Current successor:

- planning/projects/no_wli/20_active_plans/phaseB_filtered_ngram_hard_pair_report_v1_plan_2026-05-14.md
