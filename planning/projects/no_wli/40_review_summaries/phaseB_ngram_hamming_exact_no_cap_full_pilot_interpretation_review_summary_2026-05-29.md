# PhaseB N-Gram Hamming Exact No-Cap Full Pilot Interpretation Review Summary - 2026-05-29

Status: review-required
Pack subject: narrow interpretation over existing `phaseB_ngram_hamming_exact_no_cap_full_pilot_v1` outputs only

## Boundary

This interpretation uses only the completed full-pilot output files. It does not run a new scan.

```text
claim_mode = hard_pair_candidate_comparability
broad_pilot = false
full_hard_pair_report = false
production_scorer_changes = false
controlled_damage_ladder_claim = false
```

## Main Result

```text
total_hits = 14
candidates_with_hits = 3 / 10
candidates_with_zero_hits = 7 / 10
```

Hits by productive profile/order:

```text
P0 order 2 = 0
P0 order 3 = 0
P1 order 2 = 7
P1 order 3 = 0
P2 order 2 = 7
P2 order 3 = 0
```

Only `P1_word_analogue_len7_hd2` and `P2_conservative_len8_hd2` normal order 2 produced hits in this bounded sample.

## Candidate / Stratum Readout

Candidates with hits:

```text
hist_text_003fc03bd6691afe4028188f
  stratum = stable_fill
  role = none recorded
  total_hits = 6
  truth_match_ratio = 0.754

hist_text_89003ecb6b70af1e77da03a3
  stratum = current_scorer_correct_good_candidate
  role = known_better
  total_hits = 6
  truth_match_ratio = 0.754

hist_text_005c49082a5b606362401653
  stratum = stable_fill
  role = none recorded
  total_hits = 2
  truth_match_ratio = 0.585
```

Hits by stratum:

```text
current_scorer_correct_good_candidate = 6
stable_fill = 8
all other selected strata = 0
```

No hits appeared on:

```text
current_scorer_misrank_rescue_opportunity
panel_a_rescue
panel_a_break_or_likely_false_positive
high_current_score_bad_candidate
repeated_bad_candidate
low_score_control_candidate
known_worse rows
```

## Interpretation

This is still a technical/scoping readout, not a scoring-effectiveness claim.

Allowed interpretation:

```text
the no-cap hit signal is sparse in the bounded 10-candidate set
the productive signal is currently normal/order-2/P1/P2 only
the observed hits are concentrated in stable-fill and one known-better/current-correct candidate
the current bounded sample does not yet show rescue evidence
```

Forbidden interpretation:

```text
the scorer improves ranking
the scorer rescues damaged text
this validates a controlled 20-50% damage ladder
this is representative of the full hard-pair set
```

## Recommendation

If the reviewer approves expansion, keep the next bounded scan narrow:

```text
primary scan shape:
normal
order 2
P1_word_analogue_len7_hd2
P2_conservative_len8_hd2

controls:
P0 exact and/or order 3 only if reviewer wants continuity controls

before expansion:
add one bounded parity case for P2 normal order 2 on a real non-zero-hit chunk
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
