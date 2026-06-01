# v62 seed611 family compare note

Date: 2026-04-05

## Question

Does the fresh hard seed `p9/c3 seed611` repeat the same broad hard-family
shape as the known `seed411` late-stage win, or does it reveal a different
hard-seed path?

## Short answer

`seed611` is a real second hard-seed Stage 3.5 live win, but it is not the
same selector-override mechanism as `seed411`.

- `seed411`:
  - `best_match_ratio = 0.487`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - baseline candidate hash `9002ee09917e5a0d`
  - baseline source `phaseA_selected`
- `seed611`:
  - `best_match_ratio = 0.635`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline candidate hash `fe7a4d2798b221e4`
  - baseline source `phaseB_topk`

So `v62` broadens the hard-seed late-stage evidence, but it does not broaden
the specific selector-override claim that was proven on `seed411`.

## Outcome comparison

- `seed411`
  - Stage 3.5 accepted
  - runtime `4383.95s`
  - evals `4352`
  - best candidate `1fdc6d7d88e80a2b`
- `seed611`
  - Stage 3.5 accepted
  - runtime `1227.11s`
  - evals `1300`
  - best candidate `4bba54177206dd7f`

Both are `stage35_live_win` runs in the atlas, but they are different win
shapes.

## Map comparison

Shared broad structure:

- `stage2_promoted`
  - both have `24` families
  - both have largest-family share `0.0417`
- `stage3_prep`
  - both have `24` families
  - both have largest-family share `0.09375`
- `phaseC_start`
  - both have `6` rows and `6` families
- `stage35_archive`
  - both collapse to one final family

Main divergence:

- `phaseC_pool`
  - `seed411`: `34` rows, `32` families, `8` selected rows
  - `seed611`: `38` rows, `33` families, `7` selected rows
- `stage35_seed`
  - `seed411`: `2` rows in `2` families, largest-family share `0.5`
  - `seed611`: `6` rows in `2` families, largest-family share `0.8333`

Interpretation:

- `seed611` keeps a broader row set into `stage35_seed`, but it is already
  heavily concentrated into one dominant late family
- `seed411` is the sharper selector-override case, where the late seed set is
  smaller and the non-score-winner challenger matters

## What this supports

- There are at least two distinct hard-seed late-stage win shapes in the
  current programme.
- The bounded Stage 3.5 lane is not useful only on the exact `411` family.

## What this does not support yet

- a claim that the selector override itself is already broad
- a claim that all hard seeds share one structure
- a broad promotion decision

## Remaining measurement caution

At `stage35_seed`, reviewer-visible `selected_row_count` is still `0` in the
pool summary while the more useful late continuation evidence is carried in
`next_stage_started_count` and the row-level data. That is good enough for this
comparison, but it should be tightened before making stronger selected-versus-
available claims at that boundary.

## Best next step

One narrow follow-up, depending on the claim to tighten:

- if the goal is selector generality:
  - run one bounded no-selector / legacy control on `p9/c3 seed611`
- if the goal is broader taxonomy:
  - run one fresh hard seed beyond `411` and `611`
