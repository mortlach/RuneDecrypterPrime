# no-WLI Stage35 Rank-6 Route-Lineage Additive Confirmation Design

Date: 2026-04-30

## Question

Can the strict route-lineage signal be used as an additive rescue rule for
rank-6 rows rejected by the old softened rule, without reintroducing a
confirmed regression?

## Rule under test

This is not a replacement for the old softened rule.

The candidate additive rule is:

- keep rows accepted by the old softened rank-6 rule
- additionally keep old-rejected rows when:
  - `candidate_source == "phaseA_selected"`
  - `candidate_source_rank == 1`
  - `candidate_novelty_distance_to_anchor >= 173.5`

The strict route-lineage rule is not treated as a standalone replacement,
because group B in the confirmation-prep scan contains already-measured
positives that the route-only rule would reject.

## Source data

Confirmation-prep output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T151237Z__stage35_rank6_route_lineage_confirmation_prep_v1/`

Earlier shallow frontier harvest:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/`

Earlier deepening join:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/`

## Cells

Run the four group-A rows, where the old softened rule rejects but the
route-lineage additive rule keeps:

- `611/search7003`, rank `6`, candidate `826e5c871f444486`
  - prior deepening positive; reproduction/control
- `1111/search7001`, rank `6`, candidate `d94845511e181f7c`
  - key honest safety check; shallow was negative and no prior deepening row
- `1411/search7004`, rank `6`, candidate `2632e79517bf1c7c`
  - prior deepening positive; boundary reproduction/control
- `1411/search7005`, rank `6`, candidate `b47e22bc63e7c189`
  - prior deepening positive; boundary reproduction/control

Group B is logged as evidence against route-lineage replacement, not rerun in
this confirmation. The old softened rule already keeps those rows, and prior
deepening evidence includes several route-rejected positives.

## Runtime budget

Prior same-shape selected-row deepening cells in this branch were about
`75s` to `179s` each for comparable rows.

Budget:

- intended wallclock: `45m`
- hard cap: `2700s`
- per-cell rescue cap: `600s`
- stop after first executed cell if the projected serial runtime exceeds
  `2700s`

Stop conditions:

- all four cells complete
- wallclock cap reached
- first-cell projection exceeds the budget
- partial outputs remain extractable after every cell

## Success and failure criteria

Success:

- `0` runtime errors
- all four route-additive keep cells run
- no executed cell regresses versus its shallow result
- the `1111/search7001` safety-check cell is nonnegative versus shallow

Failure:

- any executed cell regresses versus shallow
- the `1111/search7001` cell remains negative versus shallow
- output cannot be extracted after partial completion

## Recommendation

Launch this tiny confirmation now under the written budget. If it passes, do
not promote directly; update the policy note to treat route-lineage as an
additive rescue hypothesis and then design the next larger confirmation around
the union rule rather than the strict route-only rule.
