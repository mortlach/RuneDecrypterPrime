# v63 seed611 legacy control note

Date: 2026-04-05

## Question

Did the selector matter on `p9/c3 seed611`, or was bounded Stage 3.5 enough by
itself on that seed?

## Short answer

On `seed611`, selector choice did not matter.

The bounded legacy/no-selector control `v63` reproduced `v62` almost exactly:

- same final `best_match_ratio = 0.635`
- same baseline candidate hash `fe7a4d2798b221e4`
- same Stage 3.5 best candidate hash `4bba54177206dd7f`
- same `1300` evals and `1` round
- slightly faster Stage 3.5 runtime in `v63`

So `seed611` is a real second hard-seed Stage 3.5 live win, but it is not a
selector-sensitive case in the same way as `seed411`.

## Direct comparison

### v62

- selector: `score_plus_novelty`
- `stage35_baseline_differs_from_phasec_score_winner = 0`
- baseline source `phaseB_topk`
- Stage 3.5 runtime `1227.11s`
- final `best_match_ratio = 0.635`

### v63

- selector: `legacy`
- `stage35_baseline_differs_from_phasec_score_winner = 0`
- baseline source `phaseB_topk`
- Stage 3.5 runtime `1186.83s`
- final `best_match_ratio = 0.635`

## Programme meaning

What this supports:

- bounded Stage 3.5 late-lane utility is broader than the exact `411`
  selector-override family
- there are now at least two distinct hard-seed win shapes:
  - `seed411`: selector-sensitive override case
  - `seed611`: selector-neutral bounded late-lane case

What this does not support:

- selector generality beyond the `411` family
- broad promotion
- a claim that all hard seeds share one structure

## Remaining measurement caution

The `stage35_seed` pool summary still under-reports the real
started-versus-available story. That does not affect the top-line `v62` vs
`v63` parity conclusion, but it does still limit stronger claims about late
seed-pool compression.

## Best next step

- sample one fresh hard seed beyond `411` and `611`
- keep selector-generalization claims narrow until another true override case
  appears
