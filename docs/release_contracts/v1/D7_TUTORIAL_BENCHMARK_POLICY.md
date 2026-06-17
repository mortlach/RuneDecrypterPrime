# D7 tutorial benchmark policy

Tutorial and benchmark runs are allowed to use known plaintext/key references when the run explicitly declares a tutorial truth policy. This is not a ciphertext-only solving claim; it is tutorial evidence and compute-efficiency instrumentation.

## Policy split

- Real solver logic must not silently depend on hidden truth data.
- Tutorial and benchmark reports may compute match ratios against known references.
- Any match-ratio/readability/target threshold must be labelled as tutorial truth use.
- Score, eval, token, and wall-time thresholds are normal benchmark controls and may be reported for every run.

## Typed framework

`rune_decrypter_prime.utils.tutorial_benchmark` defines:

- `TutorialRunKind`
- `TutorialTruthPolicy`
- `TutorialStopPolicy`
- `TutorialStopReason`
- `TutorialBenchmarkOutcome`
- `TutorialBenchmarkSummary`

The canonical JSON schema for the summary is:

```text
rdp_tutorial_benchmark_summary.v1
```

## Intended use

Long tutorials should be tuned from local evidence and should report:

- run kind
- truth policy
- readable match ratio threshold
- target match ratio threshold
- solver stop score
- eval/token/wall-time budgets where relevant
- observed match ratio where reference truth is available
- score, evals, tokens, wall time
- benchmark outcome and stop reason

## Stop semantics

A tutorial can be considered successful when it reaches either:

- target match ratio, or
- readable match ratio, when the tutorial is meant to demonstrate readability rather than exact key recovery.

A real ciphertext-only solve must continue to use solver/scorer criteria such as score thresholds, plateau, work budgets, and runtime budgets.

## D7 boundary

D7 adds the typed policy and report payload support. Full tuning of every long tutorial should be performed with local tutorial runs and committed as a follow-on tutorial rationalisation pass, not as an unvalidated late D7 expansion.
