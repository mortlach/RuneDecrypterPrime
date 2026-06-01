# Phase-C saved-surface Phase-B mass and frontload matrix plan

Date: 2026-04-18

Status:

- active
- next overnight batch
- offline exact-lane study

## Why this note exists

Candidate 3 is closed.

The first saved-pool replacement / eviction matrix is also now closed in its first
form.

That replacement batch was still useful. It showed that:

- reorder-only controls remain the only line with small positive signal
- broad non-anchor replacement did not uncover a stronger mechanism
- wider replacement mainly added harm
- width `1` replacement was not inert, but its activity was hidden by the
  top-line best-match summary

So the next mechanism question is now narrower and more specific:

- is the weak late-stage signal really about getting more of the right
  `phaseB_topk` material into the selected Phase-C starts
- and, if so, is that signal mainly about:
  - front-loading,
  - quota,
  - or a narrow `phaseB_topk`-only replacement rule?

## Main question

The question for this overnight batch is:

- how much useful `phaseB_topk` mass should the retained Phase-C selected-start
  set contain
- and in what shape should that mass appear?

This batch is deliberately not a generic replacement rerun.

It is a structured study of `phaseB_topk` mass and placement.

## Assumptions

Assume all of these remain true for this batch:

- candidate 3 stays closed
- no live runtime promotion is in scope
- this remains a fixed-instance solver-development study
- retained exact-lane semantics take priority over speculative reconstructed
  semantics

## Working rules

This batch must stay inside retained saved-surface semantics.

That means:

- use retained candidate-pool membership
- use retained selected-start identity
- use retained source order and retained `source_rank`
- do not invent a new cross-source challenger strength metric unless the
  retained artifacts clearly expose one

For this batch, “better challenger” should mean only one of these:

- earlier retained order inside a retained source bucket
- smaller retained `source_rank` where present
- explicit retained selected-start order for eviction targets

Do not introduce fresh global scoring to rank challengers across sources.

## Why this batch is worth an overnight slot

The previous replacement batch finished in about one hour.

So the next batch should be intentionally larger and should use much more of the
overnight wallclock budget.

This batch does that by staying within one mechanism family while expanding the
policy matrix enough to be informative.

The goal is not to maximise policy count blindly.

The goal is to use the overnight slot on one coherent mechanism question and
still finish the next day with a clear promote / refine / close read.

## Batch label

Use a label in this shape:

`phasec_saved_surface_phaseb_mass_and_frontload_matrix_v1`

## Core batch design

This batch has three policy blocks plus controls.

### Controls

Always include these controls:

- `source_order`
- `phaseb_topk_anchor_swap_v1`
- `phaseb_topk_frontload_all_v1`

These are the comparison floor for the rest of the batch.

### Block A - frontload depth sweep

Purpose:

- test whether the useful signal is concentrated in the first few retained
  `phaseB_topk` rows

Policies:

- `phaseb_topk_frontload_1_v1`
- `phaseb_topk_frontload_2_v1`
- `phaseb_topk_frontload_3_v1`
- `phaseb_topk_frontload_4_v1`
- `phaseb_topk_frontload_5_v1`
- `phaseb_topk_frontload_6_v1`
- `phaseb_topk_frontload_7_v1`
- `phaseb_topk_frontload_8_v1`

Semantics:

- keep the retained anchor fixed
- move the first `k` retained `phaseB_topk` challengers as early as possible
- preserve retained order inside the frontloaded block
- preserve retained order in the remainder after frontloading

Questions:

- does performance improve for the first few widths and then flatten or reverse?
- is `frontload_all` too aggressive compared with small frontload widths?

### Block B - phaseB top-k quota sweep

Purpose:

- test whether the useful signal is really about ensuring enough retained
  `phaseB_topk` representation in the selected starts, regardless of exact
  early order

Policies:

- `phaseb_topk_quota_1_v1`
- `phaseb_topk_quota_2_v1`
- `phaseb_topk_quota_3_v1`
- `phaseb_topk_quota_4_v1`
- `phaseb_topk_quota_5_v1`
- `phaseb_topk_quota_6_v1`
- `phaseb_topk_quota_7_v1`
- `phaseb_topk_quota_8_v1`

Semantics:

- keep the retained anchor fixed
- ensure at least `k` non-anchor selected starts come from retained `phaseB_topk`
- if the retained selected starts already satisfy the quota, keep retained order
- otherwise fill the quota using retained `phaseB_topk` order and then fill the
  remainder by retained source order
- do not use fresh cross-source scoring

Questions:

- does a small guaranteed `phaseB_topk` quota beat pure frontloading?
- is there a clear quota width that helps `611` / `1111` without hurting `1511`?

### Block C - phaseB top-k only replacement sweep

Purpose:

- test whether the first replacement study failed because it was too broad rather
  than because replacement is intrinsically useless

Policies:

- `phaseb_topk_replace_width_1_v1`
- `phaseb_topk_replace_width_2_v1`
- `phaseb_topk_replace_width_3_v1`
- `phaseb_topk_replace_width_4_v1`
- `phaseb_topk_replace_width_5_v1`
- `phaseb_topk_replace_width_6_v1`
- `phaseb_topk_replace_width_7_v1`
- `phaseb_topk_replace_width_8_v1`

Semantics:

- keep the retained anchor fixed
- evict the weakest retained non-anchor selected starts using retained selected
  order only
- only allow replacements from retained non-selected `phaseB_topk` challengers
- preserve retained `phaseB_topk` order inside the replacement stream
- do not pull replacement challengers from retained `phaseA_selected`
- do not use fresh cross-source scoring

Questions:

- can a narrower `phaseB_topk`-only replacement recover signal that broad
  replacement missed?
- does replacement become useful only when source restriction is strict?

## Policy count

This batch intentionally includes:

- 3 controls
- 8 frontload-depth variants
- 8 quota variants
- 8 `phaseB_topk`-only replacement variants

Total:

- 27 policies

This is intentionally much larger than the previous matrix so that the overnight
slot is used more fully while still staying inside one mechanism family.

## Cases

Run on the same retained exact-lane supported cases used in the previous
saved-surface matrix.

Do not widen the case basis in this batch.

The goal is to learn more from the same decision-gate set, not to mix in a new
basis at the same time.

## Required outputs

This batch must write all of these:

- machine-readable per-policy summary table
- machine-readable per-case delta table
- machine-readable per-policy-family summary table
- one short human readout
- one explicit promote / refine / close recommendation

## Required additional diagnostics

Because width `1` replacement was active but outcome-neutral in the previous
batch, this batch must include identity-level diagnostics, not just top-line
best-match summaries.

For every policy and every case, write:

- whether the retained selected surface changed
- winner candidate hash under control
- winner candidate hash under candidate
- winner source under control
- winner source under candidate
- whether the winner identity changed
- whether the winner lane changed
- if the policy performs explicit eviction:
  - which retained selected starts were evicted
  - which retained challengers replaced them
  - replacement source and retained rank

This is required so that “zero delta” can be separated into:

- true no-op
- active surface change with same winner
- winner change with flat top-line match

## Analysis questions for the next day

The next-day readout must answer all of these.

### Family-level questions

- is the strongest signal mainly a frontload effect, a quota effect, or a
  `phaseB_topk`-only replacement effect?
- does one family clearly dominate the others?
- does one family show a clear harm pattern on `1511`?

### Width-sensitivity questions

- for each family, does performance improve with width, flatten, or reverse?
- is there a clear sweet spot width?
- does `frontload_all` lose because it is too aggressive?

### Case-concentration questions

- are gains concentrated on `611`, `1111`, or both?
- are harms concentrated on `1511`?
- do any policies help only one case family and hurt the others?

### Identity-level questions

- when a policy is outcome-neutral, did it still change the retained start set?
- when the winner changed, did the top-line best-match remain flat?
- are the weak positives coming from stable winner changes or just equivalent
  alternative winners?

## Decision rules

### Promote to exact runtime confirmation only if

- one policy family clearly beats the controls
- one width inside that family is clearly best
- harms on `1511` are bounded
- identity-level diagnostics show a meaningful rather than purely cosmetic
  surface change

### Refine only if

- one policy family looks promising
- but the best width is still unclear
- or identity-level diagnostics show a useful mechanism that is hidden by the
  current top-line match metric

### Close if

- no policy family clearly beats the reorder controls
- or any apparent gains remain tiny and unstable
- or wider policies mainly add harm without giving a clear usable width

## Not allowed in this batch

Do not add any of these to this overnight run:

- broad generic replacement rules
- fresh cross-source scoring metrics
- exact runtime replay
- unrelated new mechanism families
- broad panel widening
- rescue-enabled extensions
- threshold grids layered on top of all three policy blocks

Keep the question narrow.

## Implementation note

Proceed directly unless one of these becomes ambiguous in code rather than in
planning:

- what counts as an eligible non-selected retained `phaseB_topk` challenger
- whether retained artifacts expose enough structure to do honest non-anchor
  eviction without inventing new semantics

If either ambiguity bites:

- stop
- write the ambiguity down explicitly
- do not patch over it with a new implicit metric
