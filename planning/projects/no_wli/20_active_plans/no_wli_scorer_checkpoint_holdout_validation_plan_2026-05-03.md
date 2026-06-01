# No-WLI Scorer Checkpoint Holdout Validation Plan

Date: 2026-05-03
Status: active report-only validation plan
Runtime status: no solver runtime change

## Question

Do the Stage 2 split-stable checkpoint-gate candidates remain useful when
validated as held-out artifact and fixture/search slices, rather than only by
aggregate S1 historical performance?

## Scope

This is a report-only validation pass over the already generated Stage 2 shadow
decision table.

It does not:

- change solver runtime behaviour
- change scorer weights
- change selection or acceptance logic
- fit learned thresholds
- add a production checkpoint gate

Truth fields remain evaluation-only.

## Candidate Rules

Only the four split-stable Stage 2 candidates are in scope:

```text
exact_span_and_repeated3_m0.02
long_span_count_m0.02_t5
long_span_count_m0.05_t5
exact_span_and_repeated3_m0.01
```

## Inputs

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_checkpoint_gate_simulation_v1/
  scorer_checkpoint_gate_simulation_pair_decisions.csv

output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_checkpoint_gate_split_validation_v1/
  scorer_checkpoint_gate_split_validation_rule_summary.csv
```

## Outputs

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_checkpoint_gate_holdout_validation_v1/
```

Expected files:

```text
scorer_checkpoint_gate_holdout_validation_rule_summary.csv
scorer_checkpoint_gate_holdout_validation_split_rows.csv
scorer_checkpoint_gate_holdout_validation_summary.json
scorer_checkpoint_gate_holdout_validation_readout.md
```

## Budget

This pass is expected to be a bounded offline table scan, not a runtime solve.

Intended wallclock budget:

```text
5 minutes
```

Stop condition:

```text
Complete all four candidate rules, or stop on missing required input files,
row-conservation failure, or malformed decision rows.
```

Progress:

```text
Print completed-versus-total candidate rules while scanning.
```

## Decision Rule

A rule may advance to fresh solver-pool or shadow-selector validation only if:

```text
aggregate net remains positive
aggregate breaks remain low
all fixture/search held-out slices with rule decisions are nonnegative
all artifact held-out slices with rule decisions are nonnegative
truth labels are used only for evaluation
```

If a rule has strong aggregate signal but negative held-out cells, it remains
diagnostic-only until a narrower rule explains the break surface.

If no candidate passes strict held-out checks, do not promote runtime behaviour.

## Expected Interpretation

Passing this check still does not approve a runtime gate. It only justifies the
next stage: fresh held-out or shadow-selector validation on candidate pools not
used to discover these rules.

## Completed Result

Run:

```text
py -3.11 tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  validate_scorer_checkpoint_gate_holdout_v1.py
```

Output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_checkpoint_gate_holdout_validation_v1/
```

Elapsed:

```text
1.62 seconds
```

Result:

```text
candidate rules: 4
strict held-out-slice pass rules: 0
runtime changed: false
truth fields evaluation-only: true
```

Rule outcomes:

```text
exact_span_and_repeated3_m0.02:
  rescues 166, breaks 6, net +160
  negative fixture/search slices: 1
  negative artifact slices: 2

long_span_count_m0.02_t5:
  rescues 140, breaks 4, net +136
  negative fixture/search slices: 0
  negative artifact slices: 2

long_span_count_m0.05_t5:
  rescues 140, breaks 6, net +134
  negative fixture/search slices: 1
  negative artifact slices: 4

exact_span_and_repeated3_m0.01:
  rescues 50, breaks 4, net +46
  negative fixture/search slices: 1
  negative artifact slices: 2
```

Interpretation:

```text
The candidate rules remain useful diagnostics, but none is clean enough to
advance directly toward runtime promotion.

The next useful work is either:
  inspect the negative held-out cells and design a narrower diagnostic rule
  or build a genuinely fresh candidate-pool/shadow-selector validation input.
```

Closeout note:

```text
planning/projects/no_wli/40_review_summaries/
no_wli_scorer_checkpoint_holdout_validation_closeout_2026-05-03.md
```
