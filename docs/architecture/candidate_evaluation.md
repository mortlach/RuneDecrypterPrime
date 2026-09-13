# Candidate evaluation

Solvers choose keys. Candidate evaluation is shared.

The materialised problem binds the runtime cipher, KeyOps, ciphertext, WLI and
scorer. Generic solvers evaluate through that boundary.

## Materialisation

`ProblemInstance` builds:

```text
runtime cipher
runtime scorer
DecryptionProblem
pipeline metadata
```

`DecryptionProblem` also constructs the KeyOps family selected by the
cipher/key-space binding.

See [Key models and search operations](key_model_and_search.md).

## Candidate path

```text
candidate key
-> split key structure if required
-> decrypt
-> apply constraints
-> score plaintext
-> numeric score
```

The solver receives the score and decides what key to try next.

## Composite keys

When interruptor positions are searched, the runtime key can contain:

```text
[core cipher key | interruptor positions]
```

The problem boundary separates those parts before decryption.

See [Interruptors](../guides/interruptors.md).

## WLI and hard constraints

WLI is checked against the plaintext length before WLI-aware scoring.

Hard crib rules can reject a candidate before ordinary scoring.

These controls change the evaluation problem. They are not presentation
settings.

## Scoring

The scorer receives plaintext candidates and WLI. It does not need to know how
the solver generated the key.

See [Scoring and language models](scoring_and_language_models.md).

## Telemetry

The problem boundary records counters including candidate evaluations, decrypt
time, score time, tokens processed and crib rejections.

See [Telemetry](../guides/telemetry.md).

## Boundary

The division is:

```text
solver  -> which key next?
problem -> what does this key decrypt to, and how does it score?
```

Keeping that boundary shared makes solver comparisons meaningful.

See [Run pipeline](pipeline.md).
