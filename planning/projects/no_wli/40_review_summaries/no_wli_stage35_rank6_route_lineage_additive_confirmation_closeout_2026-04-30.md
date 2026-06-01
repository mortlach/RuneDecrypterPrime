# no-WLI Stage35 Rank-6 Route-Lineage Additive Confirmation Closeout

Date: 2026-04-30

## Verdict

The route-lineage additive rescue rule failed the predeclared safety criterion.

It should not be promoted, widened, or used as the next runtime policy.

## Run

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_route_lineage_additive_confirmation_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153119Z__stage35_rank6_route_lineage_additive_confirmation_v1/`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_route_lineage_additive_confirmation_2026-04-30.log`

Budget:

- intended wallclock: `45m`
- hard cap: `2700s`
- per-cell cap: `600s`

Outcome:

- completed cells: `4 / 4`
- runtime errors: `0`
- elapsed: `287.159s`
- first-cell projection: `306.208s` versus `2700s`
- nonnegative versus shallow: `3 / 4`
- regressed versus shallow: `1 / 4`

Catalog and timing references were refreshed after the run:

- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153651Z__no_wli_runtime_history_reference_v1/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153651Z__fixed_runtime_wallclock_reference_v1/`

## Cell Results

Passed reproduction/control cells:

- `611/search7003`, candidate `826e5c871f444486`
  - confirmation `0.475`
  - shallow `0.464`
  - delta versus shallow `+0.011`
  - matched prior deepening exactly
- `1411/search7004`, candidate `2632e79517bf1c7c`
  - confirmation `0.404`
  - shallow `0.399`
  - delta versus shallow `+0.005`
  - matched prior deepening exactly
- `1411/search7005`, candidate `b47e22bc63e7c189`
  - confirmation `0.425`
  - shallow `0.412`
  - delta versus shallow `+0.013`
  - matched prior deepening exactly

Failed key safety cell:

- `1111/search7001`, candidate `d94845511e181f7c`
  - confirmation `0.037`
  - shallow `0.038`
  - delta versus shallow `-0.001`
  - delta versus selected start `-0.004`

## Interpretation

The route-lineage features are useful mechanism evidence, but they are not a
safe additive policy in this form.

The failure is small in magnitude but decisive for the predeclared gate,
because the key honest group-A safety cell was exactly the row that had not
already been confirmed by deepening.

The strict route-lineage rule is also not viable as a replacement rule because
the confirmation-prep group B contains old-keep / route-reject rows with
existing positive evidence.

## Prediction Comparison

Earlier prediction ledger:

- real late local-rescue phenomenon: `75-85%`
- narrow rank-or-slice policy can improve selected cases: `50-65%`
- general production policy from current signal: `25-40%`
- exact selected-start threshold `0.437` survives as-is: `15-25%`

Current comparison:

- real late local-rescue phenomenon:
  - supported
- narrow rank/slice policy improves selected cases:
  - partly supported as mechanism, not supported as a safe policy from this
    route-lineage additive rule
- general production policy from current signal:
  - not supported
- exact `0.437` threshold survives as-is:
  - not supported

## Recommendation

Close the current rank-6 route-lineage policy line as a policy candidate.

Carry forward the mechanism lesson:

- source-rank plus route novelty helps explain some rejected positives
- it does not by itself separate all additive-rescue positives from regressions

Do not launch a wider union-policy runtime. The next useful work should move
back to offline mechanism analysis or a different candidate branch, with this
route-lineage result retained as a negative safety check.
