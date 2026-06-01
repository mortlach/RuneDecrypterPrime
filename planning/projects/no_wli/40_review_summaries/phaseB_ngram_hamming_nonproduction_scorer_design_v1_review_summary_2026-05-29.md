# PhaseB N-Gram Hamming Non-Production Scorer Design v1 Review Summary - 2026-05-29

Status: review-ready
Pack subject: non-production scorer design over balanced readout v1 outputs

## Boundary

This slice uses only existing balanced readout v1 outputs. It performs no new scan and changes no production scorer behavior.

```text
claim_mode = hard_pair_candidate_comparability
scorer_design_only = true
broad_pilot = false
full_hard_pair_report = false
production_scorer_changes = false
controlled_damage_ladder_claim = false
```

## Proposed Non-Production Signal

```text
primary signal = normal_order2_P2_raw_weighted_hits
raw formula = P2 normal/order2 weighted_hit_sum
optional transform = log1p(primary_score_raw_weighted_hits)
P0 usage = audit/control only
P1 usage = redundancy comparison
```

P2 is recommended as the conservative primary under review because P1/P2 are almost identical in this readout, and P2 is the stricter named profile.

## Source Evidence

Balanced readout source:

```text
source status = pass
backend = cpp_fast
python fallback allowed = false
candidates = 118
source total hits = 328
source candidates with hits = 44
P1/P2 same-hit-count candidates = 117 / 118
P0 audit flags = 1
```

Primary-score separation by role:

```text
known_better:
  candidate_count = 40
  candidate_hit_rate = 0.500
  mean_primary_score = 20.885

known_worse:
  candidate_count = 38
  candidate_hit_rate = 0.053
  mean_primary_score = 0.978

no_recorded_pair_role:
  candidate_count = 40
  candidate_hit_rate = 0.525
  mean_primary_score = 20.464
```

Primary-score separation by stratum:

```text
known_better_pair_candidate:
  candidates_with_primary_hits = 20 / 20
  mean_primary_score = 41.771

high_truth_stable_fill:
  candidates_with_primary_hits = 20 / 20
  mean_primary_score = 39.999

known_worse_pair_candidate:
  candidates_with_primary_hits = 1 / 20
  mean_primary_score = 0.929

bad_control_candidate:
  candidates_with_primary_hits = 1 / 20
  mean_primary_score = 0.929

panel_break_known_worse:
  candidates_with_primary_hits = 1 / 18
  mean_primary_score = 1.032

panel_rescue_known_better:
  candidates_with_primary_hits = 0 / 20
  mean_primary_score = 0.000
```

Pairwise rows are diagnostic only:

```text
paired comparisons available = 2
paired comparisons preferring known-better = 1
```

The selected balanced panel does not contain enough same-pair known-better/known-worse pairs to treat pairwise preference as the main decision statistic.

## Guarded Interpretation

Allowed:

```text
P2 normal/order2 weighted hits are a plausible non-production primary signal for review
the signal separates known-better/high-truth strata from known-worse/bad-control strata in this bounded readout
P1/P2 are nearly redundant in this readout
P0 should remain an audit/control feature
```

Still forbidden:

```text
production scorer improvement claim
production scorer integration
controlled 20-50% damage-ladder claim
full hard-pair-set representativeness claim
rescue-performance claim
strict/order-4/P3/P4 expansion
```

## Review Questions

1. Is `normal_order2_P2_raw_weighted_hits` the right conservative primary signal for the first non-production scorer design?
2. Should the optional `log1p` transform be used only at combination time, rather than baked into this feature output?
3. Is P0 correctly treated as audit/control only?
4. Is P1/P2 redundancy strong enough to avoid carrying both as primary production candidates?
5. Does the zero-hit `panel_rescue_known_better` stratum block rescue claims until a targeted follow-up explains it?

## Recommended Next Decision

Review this design pack before any scorer integration. If approved, the next slice should be a non-production scorer-combination simulation that compares current score, P2 raw weighted hits, and an optional log-scaled P2 feature without changing production scoring.
