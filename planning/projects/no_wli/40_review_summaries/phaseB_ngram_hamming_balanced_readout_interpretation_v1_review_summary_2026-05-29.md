# PhaseB N-Gram Hamming Balanced Readout Interpretation v1 Review Summary - 2026-05-29

Status: review-ready
Pack subject: comparison/decision pack over balanced readout v1 outputs

## Boundary

This interpretation uses only existing balanced readout v1 outputs. It performs no new scan.

```text
claim_mode = hard_pair_candidate_comparability
broad_pilot = false
full_hard_pair_report = false
production_scorer_changes = false
controlled_damage_ladder_claim = false
```

## Source Result

```text
source_candidates = 118
source_total_hits = 328
source_candidates_with_hits = 44
```

## Separation Readout

By stratum:

```text
known_better_pair_candidate:
  candidates_with_hits = 20 / 20
  mean_hits_per_candidate = 8.000
  mean_truth_match_ratio = 1.000

high_truth_stable_fill:
  candidates_with_hits = 20 / 20
  mean_hits_per_candidate = 7.750
  mean_truth_match_ratio = 0.948

bad_control_candidate:
  candidates_with_hits = 2 / 20
  mean_hits_per_candidate = 0.250
  mean_truth_match_ratio = 0.095

known_worse_pair_candidate:
  candidates_with_hits = 1 / 20
  mean_hits_per_candidate = 0.200
  mean_truth_match_ratio = 0.115

panel_break_known_worse:
  candidates_with_hits = 1 / 18
  mean_hits_per_candidate = 0.222
  mean_truth_match_ratio = 0.216

panel_rescue_known_better:
  candidates_with_hits = 0 / 20
  mean_hits_per_candidate = 0.000
  mean_truth_match_ratio = 0.451
```

By pair role:

```text
known_better:
  candidate_count = 40
  candidates_with_hits = 20
  mean_hits_per_candidate = 4.000

known_worse:
  candidate_count = 38
  candidates_with_hits = 2
  mean_hits_per_candidate = 0.211

no_recorded_pair_role:
  candidate_count = 40
  candidates_with_hits = 22
  mean_hits_per_candidate = 4.000
```

## Profile Readout

```text
P1/P2 same-hit-count candidates = 117 / 118
P0 positive chunk rows = 1
```

This suggests P1/P2 are probably redundant for the current normal/order-2 shape, while P0 should remain an audit/control feature rather than a primary signal.

## Guarded Interpretation

Allowed:

```text
normal/order-2 tolerant n-gram Hamming signal separates high-truth/known-better candidates from known-worse/bad controls in this bounded readout
P1 and P2 are nearly redundant in this readout
P0 is mostly a control, with one exact-hit exception worth inspecting
panel_rescue_known_better zero-hit behavior blocks rescue-oriented claims for now
```

Forbidden:

```text
production scorer improvement claim
controlled 20-50% damage-ladder claim
full hard-pair-set representativeness claim
rescue-performance claim
```

## Recommendation

Move to a scorer-design slice without production behavior changes:

```text
primary candidate signal under review:
  normal/order-2/P1-or-P2 weighted hits

supporting/audit features:
  P0 exact-control hit count
  profile redundancy check
  provenance/claim-mode manifests

must investigate before claiming rescue:
  why panel_rescue_known_better rows were zero-hit
```

Still defer:

```text
strict
order 4
P3/P4
broad pilot
full hard-pair report
production scorer changes
controlled damage-ladder language
```
