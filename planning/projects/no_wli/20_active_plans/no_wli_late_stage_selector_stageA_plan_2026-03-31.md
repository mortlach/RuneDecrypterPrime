# No-WLI late-stage selector Stage A

## Purpose

Set up benchmark-only late-stage selector work on real exported data without
changing live solver behavior.

This stage is for:

- frozen frontier fixtures
- disagreement quantification
- feature-table extraction
- benchmark-only selector/reranker prototypes
- regression tests for known late-stage misselection

This stage is not for:

- live scorer replacement
- replay-driven key experiments
- full pipeline reruns using the new selector

## What is now implemented

### 1. Frozen `v45` regression fixture in the repo

Fixture:

- `tests/fixtures/no_wli/v45_seed411_late_frontier_fixture.json`

This keeps the known `seed411` late-stage failure small and reproducible inside
tests.

### 2. Benchmark-only selector / feature-table module

Module:

- `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_benchmark.py`

Capabilities:

- load frozen frontier fixtures
- summarize truth-gap dataset rows
- build a candidate feature table from a frontier
- build trial-material rows for future replay/key tests
- reproduce legacy score-led selection
- run a small weighted benchmark-only reranker
- report frontier-level selector evaluation

### 3. Initial feature surface

The current feature table includes:

- visible score fields:
  - `final_score`
  - `init_score`
  - `score_gain`
  - `init_search_score`
- structural / novelty fields:
  - `lane`
  - `source`
  - `source_rank`
  - `eligible_novel_challenger`
  - `novelty_distance_to_anchor`
- benchmark-only reference fields:
  - `final_match`
  - `init_match`
- replay-readiness flags:
  - `replay_final_key_available`
  - `replay_final_plaintext_available`
- placeholder semantic feature slots for later runs:
  - `word_ngram_score`
  - `plausible_fragment_count`
  - `longest_plausible_run`
  - `dictionary_fragment_density`
  - `garbage_penalty`

Those semantic slots remain optional and mostly empty until a fresh replay-ready
frontier is available.

### 4. Initial benchmark-only reranker prototype

The current prototype is deliberately simple:

- weighted combiner
- no truth used at selection time
- no live pipeline wiring

Current role:

- prove the benchmark harness works
- prove the frozen `v45` failure can be improved in principle
- establish a place to swap in more meaningful semantic features later

## Current proof status

Focused proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py -q`
- `7 passed`

Supporting guard slice:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_phasec_diagnostics_contract.py -q`
- `7 passed`

What is now proven:

- the frozen `v45` fixture reproduces the legacy bad choice
- disagreement reporting remains visible
- the benchmark-only reranker can choose a materially stronger explored
  challenger on the real `v45` frontier
- the Stage A harness is cheap and separate from the live pipeline

## What remains open

### 1. Semantic partial-plaintext features are still mostly placeholders

The historical `v45` frontier is not replay-material complete, so the current
frozen fixture cannot yet derive richer plaintext-driven signals directly from
stored candidate material.

### 2. The current prototype is only a first benchmark bar

It proves improvement over the known loser.
It does not yet prove broad generalisation.

### 2a. Current feature-group reading

The current generated Stage A outputs now support a stronger intermediate
reading:

- `v45` is rescued by both benchmark-only rerankers
- score-only weighting still keeps the legacy loser
- the rescue is currently driven mainly by structural / novelty signals, not by
  score-only features
- the lexical feature group is still inactive in the current Stage A pass
- the same structural / novelty rescue story now recurs across the dominant
  repeated disagreement pattern family in the real audited artifact frontiers:
  - dominant repeated pattern count `10`
  - weighted rescued count `10`
  - pairwise rescued count `10`
  - dominant weighted group counts `{ "structural_features": 10 }`
  - dominant pairwise group counts `{ "structural_features": 10 }`
- the new rescued-vs-unrecovered contrast now states the current limit in plain
  language:
  - rescued `9002...` is close enough on score and novel enough to be saved by
    the simple reranker
  - unrecovered `e45...` is still too far behind on score and has no novelty
    support in the current feature set
- the new feature audit and ablation sweep now sharpen that limit:
  - score-only rescues nothing on the current disagreement dataset
  - score+novelty rescues `13 / 14` rows across `4 / 5` patterns
  - score+lexical also rescues nothing on the current frozen frontiers
  - one-at-a-time numeric live-field additions on top of `score+novelty` also
    do not improve the current result:
    - `+ score_gap_to_winner` stays `13 / 14`, `4 / 5`
    - `+ score_gap_to_anchor` stays `13 / 14`, `4 / 5`
    - `+ init_score` stays `13 / 14`, `4 / 5`
    - `+ init_search_score` stays `13 / 14`, `4 / 5`
  - so the immediate next question is not â€œbigger modelâ€, it is:
    - are there present-but-unused live-visible features that help the
      unrecovered class before replay-ready semantic/plaintext capture exists
- one last safe source-only categorical pass now adds one useful nuance:
  - penalizing `phaseB_topk` incumbents rescues the last unrecovered pattern
  - but it does so by choosing `7391...`, not the oracle-best `e45...`
  - that makes it a promising candidate variant, not the frozen baseline
- the current `score+novelty` baseline also passes the new robustness sweep:
  - dominant `9002...` family rescued in all `81` tested perturbation configs
  - unrecovered `e45...` class rescued in `0 / 81`

Reference outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/summary.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/decision_note.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/disagreement_frontier_pattern_audit.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/rescued_vs_unrecovered_contrast.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/unrecovered_case_feature_audit.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/weighted_ablation_sweep.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/numeric_field_ablation_sweep.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/categorical_field_ablation_sweep.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/weighted_robustness_sweep.json`

### 3. Replay validation still depends on one fresh frontier

Stage B still needs one fresh comparable late-stage run with:

- `init_key_idx`
- `init_plaintext_idx`
- `final_key_idx`
- `final_plaintext_idx`

persisted for the explored frontier rows.

## Immediate next steps

1. Use the truth-gap dataset to inspect recurring winner/challenger patterns.
2. Use the rescued-vs-unrecovered contrast to identify which live-available
   non-truth features might help unrecovered `e45...`-like cases.
3. Use the present-and-used vs present-but-unused vs absent-today audit to
   decide whether the next pass should try existing fields first or wait for
   replay-ready semantic/plaintext capture.
4. Treat the tested unused numeric live fields as provisionally exhausted for
   the current frozen frontier family unless a different weighting reason
   emerges.
5. Freeze pre-`v46` Stage A baseline as:
   - `score + novelty`
   and keep the source-penalty variant as a candidate, not the baseline.
6. Decide which semantic feature subset should be added first once replayable
   plaintext/key capture is available.
7. Keep Stage A benchmark-only.
8. Do not wire the prototype into live selection until Stage B replay evidence
   exists.

## Decision checklist reference

Use:

- `planning_old/working/no_wli_stagea_decision_checklist_2026-03-31.md`

as the current gate for deciding whether Stage A evidence is strong enough to
justify moving to Stage B.

