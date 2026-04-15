# Current state

Date baseline for this summary: 2026-04-04

## Trusted conclusions

### Solver / run behaviour

- The bounded Stage 3.5 candidate lane is now a real hard-case mechanism proof
  on `p9/c3 seed411`:
  - baseline switches to the challenger family
  - Stage 3.5 accepts
  - downstream continuation reaches `best_match_ratio = 0.487`
- This is still **not** broad promotion.
  The repeated hard-case confirmation is still on the same `411` family.

### Controls

- Recent `p5/c1` and `p7/c1` controls solve cleanly under the current code.
- A benchmark-only solved short-circuit now exists as a narrow handoff fix
  using the existing `continue_after_solve` flag.
  This should stop solved controls from wasting Phase C / Stage 3.5 work.

### Mapping / atlas

- `space_map_v1` now spans:
  - `stage2_promoted`
  - `stage3_prep`
  - `phaseC_pool`
  - `phaseC_start`
  - `stage35_seed`
  - `stage35_archive`
- Parent-link kind, family-id kind, distance-to-anchor, and continuation links
  now exist in fresh artifacts.
- Stage 3 prep ancestry is still partly fallback scaffolding rather than true
  mutation ancestry.

### Stop science

- `score_stop_shadow_v2` is the right direction for stop science:
  family-aware, dump/stop split, plateau deferred.
- It should remain offline-only until the first tiny calibration panel is read.

## Current active focus

1. Hard-seed repeatability / taxonomy
   - Does the `411` hard-family shape repeat on `p9/c3 seed611`?
2. Space-map interpretation
   - Where do good hills disappear on fresh hard seeds?
3. Stop-shadow calibration
   - Can late-stage dump signals separate true near-solves from false friends?

## Current non-claims

- No broad solver promotion.
- No general claim that all hard seeds share one structure.
- No live non-oracle stop policy.
- No strong connectivity claim from Stage 3 prep ancestry yet.

## Immediate next move

Run the prepared one-job family/map collection:

- mode: `candidate_single_p9_seed611`
- experiment:
  `tune_v62_p9c3_seed611_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`

Then compare its `space_map_v1` shape to `seed411`.
