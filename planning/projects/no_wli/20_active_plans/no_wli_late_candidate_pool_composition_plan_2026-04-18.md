# Late candidate-pool composition plan

Date: 2026-04-18

Status:

- closed after Workstream 1

## Why this note exists

Candidate 3 is now operationally closed without promotion.

That closure is not a statement that candidate 3 was invalid. It is a statement
that candidate 3 remained a small, case-dependent late-start reorder effect and
did not justify more overnight runtime use in the current line.

The carry-forward lesson is still useful:

- the exact saved-surface lane was worth building
- narrow late-surface questions can now be tested cleanly
- the next mechanism question should move from late-start ordering to late-pool
  composition

## Working basis

This plan keeps the current fixed-instance solver-development basis:

- frozen `p9 / c3 / l1000 / no-WLI` panel
- primary trio:
  - `1511` = strongest positive control
  - `611` = best middle unsolved case
  - `1111` = clearest conversion-failure case
- `1411` remains a caveated cross-check, not a first-line tuning target

This plan does not reopen:

- candidate 1
- candidate 2
- candidate 3
- broad panel expansion
- live promotion requests

## Main question

The next mechanism question is:

- not which saved late start goes first
- but which late starts should exist in the pool at all

In plain English:

- candidate 2 showed that slack-style family preservation was too weak
- candidate 3 showed that reordering the same pool can matter, but only weakly
  and inconsistently
- the next likely gain is therefore true late-pool replacement / eviction, not
  another reorder-only variant

## Overnight resource rule

Overnight runtime is the scarce resource in this line.

So the working rule is:

- offline saved-surface screens may be batched overnight
- daytime analysis is the gate for what deserves the next overnight slot
- no broad runtime replay batch should run unless the mechanism and the decision
  gate are already narrow
- every overnight batch must end with one of:
  - promote
  - refine
  - close

## Outcome to date

- Workstream 1 is complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T193551Z__phasec_saved_surface_pool_replacement_matrix_v1/`
- Outcome:
  - recommendation: `close`
  - best replacement policy: `pool_replace_width_1_v1`
- Short read:
  - `pool_replace_width_1_v1` was the least harmful replacement rule and it did
    change the saved start set on all `19` cases, but it remained
    outcome-neutral on best-match ratio and did not beat reorder-only controls
    on any usable decision gate
  - `pool_replace_width_2_v1` and `pool_replace_width_3_v1` introduced harm
    without producing any replacement wins
  - `pool_replace_width_cap_all_v1` was clearly too aggressive and turned
    `6/10` usable decision gates negative
  - the reorder-only controls remained stronger than every replacement width:
    - `phaseb_topk_anchor_swap_v1`: `3` positive, `6` neutral, `1` negative
    - `phaseb_topk_frontload_all_v1`: `4` positive, `4` neutral, `2` negative
- Decision:
  - close the current replacement / eviction line
  - do not launch Workstream 2 under the current width/eviction semantics
  - do not launch Workstream 3 for this rule family

## Workstream 1 - saved-pool replacement / eviction matrix

Status:

- complete
- closed as a valid negative

Question:

- does true late-pool replacement beat reorder-only controls on the exact
  saved-surface lane?

Why this is first:

- this is the first direct test of the missing mechanism
- candidate 2 did not truly replace or evict
- candidate 3 only changed start order inside the same pool

Overnight batch type:

- offline
- saved-surface
- batched

Inputs:

- retained Phase-C candidate pool rows
- retained Phase-C start identities
- retained fixed-panel supported exact-lane cases

Control policies to include:

- `source_order`
- `phaseb_topk_anchor_swap_v1`
- `phaseb_topk_frontload_all_v1`

Replacement policies to include in the first batch:

- replace width `1`
- replace width `2`
- replace width `3`
- replace width `cap_all`

First-batch replacement rule:

- keep the retained anchor fixed
- replace the weakest non-anchor selected starts
- use the strongest eligible non-selected challengers from the retained late pool
- prefer simple `phaseB_topk`-first challenger sourcing in the first batch
- do not add threshold conditions yet

Required outputs:

- machine-readable summary table
- case-level delta table
- one short human readout
- explicit promote / refine / close recommendation

What we want to see:

- whether any replacement width clearly beats reorder-only controls
- whether gains appear on `611`, `1111`, or both
- whether harm concentrates on `1511`
- whether one width looks clearly better than the others

Decision rule after Workstream 1:

- promote:
  - one width rule is clearly better than reorder controls and harms are bounded
- refine:
  - replacement helps, but only with a mixed harm profile
- close:
  - replacement does not beat reorder-only controls

Outcome:

- recommendation: `close`
- best replacement width: `1`
- no replacement width beat the reorder-only controls on usable decision gates
- `width 1` stayed at `0` positive / `10` neutral / `0` negative and was
  active-but-neutral:
  - it changed the saved start set on all `19` cases
  - it left the winning candidate hash and winner source unchanged on all `19`
    cases
- `width 2` and `width 3` introduced harm without any wins
- `cap_all` was clearly harmful at `0` positive / `4` neutral / `6` negative

## Workstream 2 - conditioned replacement sweep

Status:

- not authorized
- Workstream 1 closed the current line before conditioning

Question:

- can one simple deterministic condition keep the gain from replacement while
  reducing harm?

Why this is second:

- if raw replacement helps at all, the next likely gain is in deciding when
  replacement should happen, not in widening it blindly

Gate read from Workstream 1:

- not reached
- no replacement width produced a useful signal to condition

Overnight batch type:

- offline
- saved-surface
- batched

Inputs:

- best one or two widths from Workstream 1 only
- same retained exact-lane case set

Condition families allowed in this batch:

- challenger-minus-weakest-selected margin threshold
- challenger rank threshold
- anchor-challenger gap threshold
- novelty / distinctness threshold
- source restriction:
  - `phaseB_topk` only
  - or full eligible pool

Not allowed in this batch:

- new runtime policies
- broad width re-sweeps
- large multi-factor grids that make next-day interpretation unclear

Required outputs:

- machine-readable summary table
- case-level delta table
- one short human readout
- benefit-versus-harm frontier summary
- explicit promote / refine / close recommendation

What we want to see:

- one simple condition that preserves most of the gain from Workstream 1
- less harm on positive-control cases
- a rule that remains easy to explain and test

Decision rule after Workstream 2:

- promote:
  - one conditioned rule is clearly cleaner than unconditional replacement
- refine:
  - signal exists, but the rule is still too messy or too sensitive
- close:
  - conditioning does not improve the trade and mostly creates noise

## Workstream 3 - exact runtime confirmation of the winning mechanism

Status:

- not authorized
- no winning saved-surface replacement rule was produced

Question:

- does the winning saved-surface mechanism survive real runtime replay closely
  enough to justify a new narrow runtime candidate?

Overnight batch type:

- runtime
- exact
- narrow

Inputs:

- exact control replay
- exact matched candidate replay
- smallest case set needed to make a decision

Default case set:

- `611`
- `1111`
- `1511`

Optional cross-check:

- `1411`, only if the read actually needs a mixed context case

Gate read from prior workstreams:

- not reached
- there is no saved-surface replacement winner to justify exact runtime replay

Required outputs:

- retained versus replay surface comparison
- control versus candidate exact delta table
- one short human readout
- runtime-cost summary
- explicit promote / refine / close recommendation

What we want to see:

- control replay is close enough to retained reference to be trusted
- candidate improves target cases by more than replay drift
- candidate does not introduce unacceptable harm on `1511`

Decision rule after Workstream 3:

- promote:
  - candidate survives exact runtime confirmation cleanly
- refine:
  - runtime decision is blocked mainly by replay fidelity, not candidate utility
- close:
  - saved-surface effect does not survive runtime reality

## Common analysis contract

Every overnight batch must produce all of these:

- one machine-readable summary table
- one case-level delta table
- one short human readout
- one explicit promote / refine / close recommendation

Every analysis readout must answer these questions:

- what exact mechanism was tested?
- what was the control?
- what improved?
- what got worse?
- where was the effect concentrated?
- was the effect larger than the local drift / noise band?
- what should happen next:
  - promote
  - refine
  - or close?

## Current stop point

This line stopped early at Workstream 1.

Current read:

1. Workstream 1 completed and closed the line cleanly.
2. Workstream 2 is not authorized for the current width/eviction rule family.
3. Workstream 3 is not authorized for the current width/eviction rule family.

If this theme is reopened later, it should be with a genuinely different
late-pool mechanism rather than conditioned tuning of the current replacement
heuristic.

## Not in scope

This plan does not authorize:

- more candidate 3 replay
- more reorder-only runtime variants
- broad benchmark widening
- live runtime promotion before exact confirmation
- large overnight runtime batches with unclear decision gates
- conditioned replacement sweep for the current width/eviction rule family
- exact runtime confirmation for the current width/eviction rule family
