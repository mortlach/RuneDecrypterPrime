# Durable cipher-development lessons

These are operating rules distilled from completed investigations. Raw logs,
campaign tables and obsolete plans belong in external evidence or Git history.

## Diagnose scoring before increasing search

Replay the same deterministic failed case and determine whether truth is
generated but mis-ranked before increasing population, restarts or runtime.

## Select by search-visible score only

Multi-attempt winners are selected from valid results by solver score, with a
deterministic tie break. Plaintext match and key truth are evaluated only after
selection.

## Freeze candidate recipes during qualification

Keep cipher range, scorer, budget, attempt count and acceptance rule together
under one versioned recipe. A changed recipe starts new evidence; it does not
resume or overwrite old evidence.

## Separate stochastic failure from systematic mis-ranking

Repeat a frozen case with deterministic seeds. Distinguish failure to generate
a useful candidate from a scorer that ranks a known better candidate lower.

## Preserve exact replayable evidence

Persist candidate identity, payload, named scores, seed, recipe and asset
provenance—not only the best score. Truth-bearing terminal assessment stays
separate from search-visible artifacts.

## Smoke checks are engineering evidence

A smoke run demonstrates construction, determinism, bounded execution and
artifact validity. It does not establish solver quality or promote a recipe.

## Keep investigations local

Do not turn one experiment into another solver, scorer, campaign, registry or
public retry framework. Promote only stable behaviour with a clear independent
production use.
