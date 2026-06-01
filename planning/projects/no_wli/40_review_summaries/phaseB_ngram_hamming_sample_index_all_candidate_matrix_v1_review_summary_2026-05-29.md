# PhaseB N-Gram Hamming Sample-Index All-Candidate Matrix v1 Review Summary - 2026-05-29

Status: review-ready
Pack subject: asset provenance checkpoint plus sample-index all-candidate matrix and interpretation

## Boundary

This is a sample-index matrix, not a full raw n-gram rebuild result.

```text
claim_mode = hard_pair_candidate_comparability
dataset_status = sample_index_confirmed
full_raw_ngram_rebuild_confirmed = false
production_scorer_changes = false
controlled_damage_ladder_claim = false
full_hard_pair_report = false
rescue_performance_claim = false
```

## Asset Provenance

The current n-gram Hamming phrase index is internally consistent and points to:

```text
asset_root = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_index_v1/20260514T044954Z__phaseB_filtered_ngram_index_v1
run_mode = sample
sample_line_limit_per_order = 25000
phrase_entry_count = 196680
phrase_index_sha256 = ded2c46e9fa27ff4ea6cd126bd0d3d3f59da86b73a11a254e8cbe0c21bf733e5
```

Available sample assets:

```text
cuts = normal, strict
directions = fwd, rev
orders = 2, 3, 4, 5
asset_file_count = 16
```

Latest scans before this matrix used:

```text
cut = normal
direction = fwd
order = 2
sample phrase index = true
```

## Matrix Scope

```text
run = phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1
status = pass
backend = cpp_fast
python_fallback_allowed = false
candidates = 604
chunks = 1208
scan_cells = 3624 / 3624
profiles = P0, P1, P2
cut/order = normal / 2
elapsed_seconds = 386.052
measured_attempts_per_second = 16394011.827
total_hits = 1051
candidates_with_hits = 243 / 604
```

Implementation hardening:

```text
matrix runner monkeypatch wrapper removed
balanced runner global mutation = false
standalone matrix run loop = true
regression test for balanced config non-mutation = present
refreshed rerun log = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1/sample_index_matrix_refactor_rerun_2026-05-29.log
```

Profile hits:

```text
P0_exact_short = 1
P1_word_analogue_len7_hd2 = 533
P2_conservative_len8_hd2 = 517
```

Role hits:

```text
known_better = 1026
known_worse = 24
mixed_pair_role = 1
```

## Pairwise Interpretation

All `2594` hard-pair rows were evaluated with:

```text
current_score_only
p2_raw_weighted_hits_only
current_score_plus_log1p_p2
gated_current_plus_log1p_p2
```

Pairwise preference readout:

```text
current_score_only:
  known-better preferred = 1992 / 2594
  known-worse inversions = 602 / 2594
  inversion rate = 0.232074

p2_raw_weighted_hits_only:
  known-better preferred = 572 / 2594
  known-worse inversions = 280 / 2594
  ties = 1742 / 2594
  inversion rate = 0.107941

current_score_plus_log1p_p2:
  known-better preferred = 1804 / 2594
  known-worse inversions = 790 / 2594
  inversion rate = 0.304549

gated_current_plus_log1p_p2:
  known-better preferred = 618 / 2594
  known-worse inversions = 236 / 2594
  ties = 1740 / 2594
  inversion rate = 0.090979
```

High-truth versus bad-control:

```text
P2 raw mean margin = 24.306748
P2 raw inversion rate = 0.022571
gated blend mean margin = 2.865460
gated blend inversion rate = 0.022571
```

Balanced high-truth stable fill versus bad-control:

```text
P2 raw mean margin = 39.070103
P2 raw inversions = 0 / 400
gated blend mean margin = 3.992810
gated blend inversions = 0 / 400
```

Panel rescue remains blocked:

```text
panel_rescue_known_better candidates = 20
P2-hit candidates = 0
```

## Guarded Interpretation

Allowed:

```text
the current sample-index P2 signal is strongly concentrated in known-better candidates
P2 raw and gated blend reduce known-worse inversion rate compared with current score
P2 raw/gated modes leave many pairwise ties because many pairs have zero P2 signal
the naive current+log1p(P2) blend is not approved by this readout because it increases known-worse inversions
```

Still forbidden:

```text
production scorer integration
production scorer improvement claim
full raw n-gram claim
controlled 20-50% damage-ladder claim
rescue-performance claim
strict/order-4/P3/P4 expansion
```

## Review Questions

1. Should the next scorer simulation prefer the gated blend over the naive blend, given its lower inversion rate but many ties?
2. Is P2 raw now better treated as a filter/audit feature than as a standalone ranker, because it produces many zero-score ties?
3. Do we need a full raw n-gram rebuild before any further scorer-combination work, or is one more sample-index calibration slice useful?
4. Should the next sample-index slice add normal/order-3 P2 only, or stop and rebuild full raw assets first?
5. Does `panel_rescue_known_better = 0 / 20` require a targeted rescue diagnostic before any rescue-oriented expansion?
