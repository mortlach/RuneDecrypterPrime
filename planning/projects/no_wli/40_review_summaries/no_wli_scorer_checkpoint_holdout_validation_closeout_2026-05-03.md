# No-WLI Scorer Checkpoint Holdout Validation Closeout

Date: 2026-05-03
Runtime status: no solver runtime change

## What Ran

Implemented and ran:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
validate_scorer_checkpoint_gate_holdout_v1.py
```

Focused tests:

```text
py -3.11 -m pytest
  tests/tools/test_no_wli_scorer_checkpoint_gate_holdout_v1.py
```

Result:

```text
4 passed
```

Validation output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_checkpoint_gate_holdout_validation_v1/
```

## Scope

This is stricter held-out-slice validation over the existing Stage 2 shadow
decision table.

It is not fresh solver-pool validation.

No runtime selector, scorer, or acceptance behavior changed.

Truth labels were used only for evaluation.

## Candidate Rules

```text
exact_span_and_repeated3_m0.02
long_span_count_m0.02_t5
long_span_count_m0.05_t5
exact_span_and_repeated3_m0.01
```

## Result

```text
strict holdout pass rules: 0 / 4
```

Rule summary:

```text
exact_span_and_repeated3_m0.02:
  rescues 166
  breaks 6
  net +160
  negative fixture/search slices 1
  negative artifact slices 2

long_span_count_m0.02_t5:
  rescues 140
  breaks 4
  net +136
  negative fixture/search slices 0
  negative artifact slices 2

long_span_count_m0.05_t5:
  rescues 140
  breaks 6
  net +134
  negative fixture/search slices 1
  negative artifact slices 4

exact_span_and_repeated3_m0.01:
  rescues 50
  breaks 4
  net +46
  negative fixture/search slices 1
  negative artifact slices 2
```

## Decision

Do not promote these rules directly toward runtime behavior.

The aggregate signal is still useful, but the held-out break surface is not
clean enough for a checkpoint gate.

## Next Work

Best next options:

```text
1. Inspect the negative held-out cells and identify whether a simple
   non-truth feature explains them.

2. If no clean explanation exists, build a genuinely fresh candidate-pool or
   shadow-selector validation dataset before any runtime-gate work.
```

Do not launch a long runtime scan from these rules as-is.
