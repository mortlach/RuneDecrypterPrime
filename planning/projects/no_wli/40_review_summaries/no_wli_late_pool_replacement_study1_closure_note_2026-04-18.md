# Late pool replacement Study 1 closure note

Date: 2026-04-18

Status:

- closed

## Question

Study 1 asked:

- does true late-pool replacement beat reorder-only controls on the exact
  saved-surface lane?

## Batch output

- output bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T193551Z__phasec_saved_surface_pool_replacement_matrix_v1/`
- main readout:
  - `phasec_saved_surface_pool_replacement_readout.md`
- machine summary:
  - `phasec_saved_surface_pool_replacement_summary.json`
- recommendation:
  - `close`

## Decision

Study 1 is a valid negative and closes the current late-pool replacement /
eviction line.

It does not justify:

- promotion
- a conditioned replacement sweep
- exact runtime confirmation for this rule family

## What was tested

Control policies:

- `source_order`
- `phaseb_topk_anchor_swap_v1`
- `phaseb_topk_frontload_all_v1`

Replacement policies:

- `pool_replace_width_1_v1`
- `pool_replace_width_2_v1`
- `pool_replace_width_3_v1`
- `pool_replace_width_cap_all_v1`

Replacement rule:

- keep the retained anchor fixed
- replace the weakest non-anchor selected starts
- source challengers from the retained late pool
- prefer `phaseB_topk` challengers ahead of `phaseA_selected`

## Main result

No replacement width beat the reorder-only controls on usable decision gates.

The least harmful replacement rule was `pool_replace_width_1_v1`, but it was
active rather than inert:

- `0` positive
- `10` neutral
- `0` negative

Width `1` changed the retained Phase-C start set on all `19` cases, but it was
outcome-neutral on best-match ratio across all `19` cases:

- one retained non-anchor start was evicted on every case
- one challenger from the retained late pool was inserted on every case
- the winning candidate hash stayed the same on all `19` cases
- the winning source stayed the same on all `19` cases
- candidate minus control stayed `0.000` on all `19` cases

That means it avoided new harm, but it still did not produce the gain that
would justify a second study.

The wider replacements were worse:

- `width 2`: `0` positive, `9` neutral, `1` negative
- `width 3`: `0` positive, `8` neutral, `2` negative
- `cap_all`: `0` positive, `4` neutral, `6` negative

The reorder-only controls remained stronger:

- `phaseb_topk_anchor_swap_v1`: `3` positive, `6` neutral, `1` negative
- `phaseb_topk_frontload_all_v1`: `4` positive, `4` neutral, `2` negative

## What we think is happening

The current replacement / eviction semantics do not reveal a stronger missing
late-pool mechanism.

The most plausible read is:

- replacing one weak non-anchor does change the saved start set, but in this
  rule family it mostly touches non-decisive rows rather than the eventual
  winning row
- wider eviction increasingly removes starts that the retained pool still needs
  on positive-control and mixed lanes
- the useful signal in this area remains more about narrow reorder choices than
  about the current simple eviction rule

## Carry-forward lesson

This is still useful evidence.

It says:

- the exact saved-surface lane was strong enough to close this question cleanly
- true improvement did not appear under the current replacement heuristic
- if late-pool composition is revisited later, it should be with a genuinely
  different mechanism rather than threshold-tuning the same weakest-evict rule

## Next move

Do not run:

- Study 2 conditioned replacement sweep
- Study 3 exact runtime confirmation for this rule family

The next honest move is:

- close this line in planning
- carry forward the saved-surface evaluation method
- choose a different mechanism question
