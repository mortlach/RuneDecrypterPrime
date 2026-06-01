# Tactical Refactor Filter For Solve-First Work

Date: 2026-03-21
Status: Working decision memo
Scope: `tools/benchmarks/periodic_sub_trans/no_wli`

## Purpose

This memo is not a refactor plan.
It is a filter for deciding which refactors are worth doing while the solve programme is still the main priority.

The working brief already says that hard-solve progress comes before broad tidy-up, and that tactical refactor is allowed only when it directly protects or accelerates the solve programme.

## Core Rule

A refactor is justified now only if it does at least one of these:

- protects execution semantics
- protects determinism
- improves auditability or traceability
- makes experiments faster or safer to run
- makes an important next method family materially easier to add

If it mainly improves neatness, symmetry, naming purity, or architectural beauty, it should usually wait.

## Refactor Types Worth Doing Now

### 1. Contract hardening

Anything that makes requested versus actual stage behaviour explicit is worth doing now.
The invalid Stage-3.5 proof is the clearest example of why this matters.

### 2. Determinism and repeatability safeguards

If refactoring is needed to make seed propagation, backend parity, or stage repeatability explicit, that is worth doing now.

### 3. Trace and artefact clarity

Anything that makes it easier to tell what ran, what did not run, why, and with what exact config is worth doing now.

### 4. Extension points for clearly chosen next methods

If a small refactor makes late judges, stronger local moves, or temperature-based multi-chain search much easier to add cleanly, that can be justified now.

### 5. Benchmark and metric plumbing

Refactors that make the benchmark ladder, chunk metrics, or acceptance logic first-class are justified, because they improve the programme's ability to measure real progress.

## Refactor Types That Should Usually Wait

### 1. Broad architectural tidy-up

Do not reorganise the whole codebase just because it looks untidy.
The reports do not support the claim that general engineering mess is the main blocker.

### 2. Abstraction-first redesign

Do not introduce more layers, wrappers, or generic frameworks unless a specific next method actually needs them.

### 3. Interface simplification that risks semantic drift

If a cleanup changes meaning, stage behaviour, or scoring semantics, it is too risky unless tied to a specific solve or measurement need.

### 4. Refactors whose benefit is mostly aesthetic

Naming clean-up, module reshuffles, or pattern-consistency work should not outrank basin recovery, benchmark measurement, or stronger search.

## Practical Filter Questions

Before approving a refactor during solve-first work, ask:

1. Does this reduce the chance of silent semantic drift?
2. Does this make experiments easier to trust or compare?
3. Does this directly help the next chosen solve method?
4. Does this reduce run cost, review cost, or debugging cost?
5. Would we still choose this change if no one ever praised the neatness?

If the answer is no to most of these, it is probably not a now-refactor.

## Examples

A good now-refactor:

- making late-judge hooks explicit so stronger rerankers can be added without ambiguity
- tightening artefact emission so stage execution cannot be misread

A bad now-refactor:

- flattening or renaming large module families just to make the tree prettier

A borderline case:

- consolidating duplicate stage-config logic

This is only worth doing now if it reduces real semantic-drift risk or makes experiment setup materially safer.

## Bottom Line

The project should remain solve-first.
Refactor is justified now only when it protects truth, determinism, auditability, experiment speed, or the next real method extension.

Everything else is later work.
