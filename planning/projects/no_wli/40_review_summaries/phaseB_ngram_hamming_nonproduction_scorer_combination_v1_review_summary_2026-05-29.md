# PhaseB N-Gram Hamming Non-Production Scorer Combination v1 Review Summary - 2026-05-29

Status: review-ready
Pack subject: non-production scorer-combination simulation over balanced readout design rows

## Boundary

This slice uses existing non-production scorer-design rows only. It performs no new scan and changes no production scorer behavior.

```text
claim_mode = hard_pair_candidate_comparability
scorer_design_only = true
broad_pilot = false
full_hard_pair_report = false
production_scorer_changes = false
controlled_damage_ladder_claim = false
```

## Compared Modes

```text
current_score_only
p2_raw_weighted_hits_only
current_score_plus_log1p_p2
```

The combined mode is exactly:

```text
current_score + log1p(P2 raw weighted hits)
```

The raw P2 weighted hit count remains separately inspectable.

## Separation Readout

Known-better versus known-worse:

```text
current_score_only:
  mean margin = 0.157779
  undesired cross-stratum inversion rate = 0.213158

p2_raw_weighted_hits_only:
  mean margin = 19.907640
  undesired cross-stratum inversion rate = 0.026316
  ties = 720 / 1520

current_score_plus_log1p_p2:
  mean margin = 1.879158
  undesired cross-stratum inversion rate = 0.227632
```

High-truth stable fill versus bad control:

```text
current_score_only:
  mean margin = 0.241644
  undesired cross-stratum inversions = 0 / 400

p2_raw_weighted_hits_only:
  mean margin = 39.070103
  undesired cross-stratum inversions = 0 / 400

current_score_plus_log1p_p2:
  mean margin = 3.800268
  undesired cross-stratum inversions = 0 / 400
```

Panel rescue known-better behavior:

```text
panel_rescue_known_better candidates = 20
P2-hit candidates = 0
top20 count under current+log1p(P2) = 0
```

This remains a hard block on rescue-performance claims.

## Same-Pair Inversion Readout

Only `2` same-source-pair known-better/known-worse comparisons are present in this balanced panel.

```text
current_score_only:
  known-better preferred = 1
  known-worse preferred = 1

p2_raw_weighted_hits_only:
  known-better preferred = 1
  known-worse preferred = 0
  ties = 1

current_score_plus_log1p_p2:
  known-better preferred = 1
  known-worse preferred = 1
```

The combined mode inherits one current-score inversion where both candidates have zero P2 signal.

## Guarded Interpretation

Allowed:

```text
P2 raw weighted hits gives the strongest group separation among the three tested modes
current+log1p(P2) preserves positive mean separation but can inherit current-score inversions when P2 is zero
high-truth stable fill remains cleanly separated from bad controls in all three modes
panel_rescue_known_better remains zero-hit and does not support rescue claims
```

Still forbidden:

```text
production scorer integration
production scorer improvement claim
controlled 20-50% damage-ladder claim
full hard-pair-set representativeness claim
rescue-performance claim
strict/order-4/P3/P4 expansion
```

## Review Questions

1. Should the next non-production simulation prefer P2 raw weighted hits over the naive current+log1p(P2) blend?
2. If a blend is still desired, should it use a gated form that does not let current score dominate zero-P2 pairs?
3. Is the same-pair comparison count too small to drive decisions, leaving cross-stratum separation as the main readout?
4. Does the zero-hit panel-rescue behavior require a targeted rescue-diagnostic slice before any broader expansion?
5. Is it acceptable to keep strict/order-4/P3/P4 deferred until the P2/current combination question is settled?

## Recommended Next Decision

Review before integration. The strongest immediate read is that P2 raw weighted hits is cleaner than the naive current+log1p(P2) blend for this bounded panel, while the blend may still be useful later with gating or calibration.
