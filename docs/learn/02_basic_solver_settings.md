# Basic solver settings

New term? See the [learner glossary](00_words_used_here.md).

For the learning examples, Beam only needs a few ideas.

```text
width      how many candidate keys stay alive
rounds     how many times Beam expands and re-ranks them
restarts   how many fresh searches to try
plateau    stop if the best score stops improving
seed       make random choices repeatable
target     stop if a chosen score is reached
```

That is the useful beginner version.

## Width

```text
width = 16
```

means:

> keep the best 16 candidate keys after each round.

Larger width keeps more alternatives alive, but does more work.

The ordinary default is `width=64`. The `16` above is an example of a smaller beam.

## Rounds

One round is:

```text
take current candidate keys
-> make legal variations
-> score them
-> keep the best ones
```

In RDP:

```text
rounds = 0
```

means:

> choose the number of rounds automatically.

It does **not** mean zero work.

The current automatic rule is:

```text
max(2 * key_length, 12)
```

Examples:

```text
key length 3    12 rounds
key length 8    16 rounds
key length 13   26 rounds
```

These are round budgets; an earlier stop can end the search. For a first run,
automatic rounds are fine.

## Restarts

```text
restarts = 1
```

means:

> run one Beam search.

A larger value starts again from a fresh set of candidate keys and keeps the
best result across those searches.

Use more restarts when you want another independent attempt from a different
starting population.

## Plateau

A plateau is a stretch where the best score is no longer improving enough.

```text
plateau_rounds = 16
```

roughly means:

> if the search has gone 16 rounds without useful improvement, stop.

This saves work when the search appears stuck. The omitted plateau setting
currently becomes 16 rounds at execution; it does not disable plateau stopping.

You can ignore plateau settings for the first learning examples.

## Seed

```text
seed = 12345
```

means:

> use the same random choices again next time.

The seed does not change the cipher.

It makes solver randomness reproducible. An omitted seed is recorded as
`None`, with effective seed `0`. This is deterministic, not a fresh random
seed each time. Repeatability assumes the same data, configuration and runtime.

If two people use the same input, same settings and same seed, they can compare
the same search rather than merely similar searches.

## Target score

```text
target_score = ...
```

means:

> stop early if the score reaches this value.

Only use this when you have a justified score target.

A score is not proof of a correct decrypt, so arbitrary targets are not very
useful.

See [What can the score tell you?](05_scoring_limits.md).

## What should I change first?

For a beginner:

```text
first change       key length
second change      cipher hypothesis
then compare       width or search budget
usually leave      seed, restarts, plateau, target
```

The important habit is still:

> change one thing, then compare.

Next: [Search a key](02_search_a_key.md).

For every Beam option, see the full
[solver parameter reference](../reference/parameters/solvers.md).
