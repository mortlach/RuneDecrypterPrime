# `score_stop_shadow_v2` experiment plan

## Objective

Run a disciplined offline pass that tests whether family-aware score/trust
signals can identify rows worth:

1. dumping for inspection early
2. later using as a conservative shadow stop proxy

This plan assumes current repo/output shape from the 2026-04-03 snapshot.

## Why this is worth doing now

The current repo already has:

- `space_map_v1` rows across:
  - `stage2_promoted`
  - `stage3_prep`
  - `phaseC_pool`
  - `phaseC_start`
  - `stage35_seed`
  - `stage35_archive`
- replay helpers that rebuild:
  - cipher runtime
  - full/search/judge scorers
  - word-ngram report scorer
- Stage 3.5 progress dumps for newer artifacts

So this is a good time to test **shadow** stop logic without changing solver
behaviour.

## Main hypothesis

Near-solved rows are not just high-scoring.
They tend to sit in a region that is simultaneously:

- high-trust text
- ahead of rival families in the same pool
- supported by more than one row in that family when possible
- stable across more than one saved boundary

False friends should fail at least one of those conditions often enough to keep
false-stop risk low.

## First-pass questions

### Q1. Dump trigger

Can a family-aware trust rule mark rows that are worth saving for inspection
without many false positives?

### Q2. Stability stop proxy

If a family stays trigger-positive across more than one boundary, does that
separate true or near-true solutions from false friends well enough to justify
future stop-policy research?

### Q3. Savings potential

When the trigger fires on fixture runs, how much stage/runtime work might have
been saved by earlier inspection or stopping?

## Scope of the first run panel

Use a very small, heterogeneous panel first.

Required categories:

1. one solved easy/medium control
   - ideally fresh `p5` or `p7`
2. one hard `411` live success / Stage 3.5 win
3. one hard non-solved or non-dominant-family `p9` case

This is enough to test separation without pretending broad generality.

## Recommended execution order

### Phase A. Build row table only

Run the extractor on the small panel and verify:

- rows load without crashing
- replay scorers build where expected
- plaintext decrypt fallback works for key-only rows
- row-level replay fields populate sensibly
- data gaps are explicit rather than silent

Success criterion:

- `row_scores.jsonl` is complete enough to inspect by eye

### Phase B. Dump-trigger sweep

Run the full threshold grid and inspect:

- which rows become `would_dump`
- whether solved/near-solved rows trigger early
- whether obvious false friends also trigger

Success criterion:

- at least one rule looks promising on the small panel
- false positives are understandable, not chaotic

### Phase C. Stability stop sweep

Enable only the family-stability stop proxy and inspect:

- does requiring repeated family dominance reduce false positives materially?
- do solved/near-solved rows still trigger?

Success criterion:

- at least one stability rule has zero false stops on solved controls
- and still catches the hard success case

### Phase D. Read savings proxy carefully

Do not oversell the savings numbers.

In v2, treat them as coarse proxies from:

- stage boundary order
- available late runtime fields
- Stage 3.5 progress when present

Success criterion:

- useful relative comparisons
- not precise wallclock claims

## Main outputs to read first

1. `threshold_sweep_summary.json`
2. `run_shadow_summary.jsonl`
3. `data_gap_report.json`
4. a small manual inspection of a few rows in `row_scores.jsonl`

## Readout questions

### Dump rule readout

- which rule first separates the solved control from obvious false friends?
- which rule catches the hard `411` success without many junk triggers?

### Stop rule readout

- does requiring repeated boundary support help enough to make stop science
  credible?
- or does it mostly fire too late to save anything useful?

### Data gap readout

- which stage boundaries still fail to provide enough plaintext/scorer/trust
  evidence?
- is the main blocker missing data, or weak separability?

## Pass / pause criteria

### Pass to wider calibration

Only if all are true:

- at least one dump rule looks useful on the small panel
- at least one stability rule has zero false stops on the solved control
- the hard success case is caught by a plausible rule
- data gaps are manageable and explicit

### Pause and improve data/telemetry first

If any of these dominate:

- too many rows cannot be replay-scored
- word-ngram runtime is missing on most useful rows
- family margins are too often undefined
- triggers are mostly noise across all threshold settings

## What not to do after the first pass

- do not wire any live stop rule directly
- do not collapse dump and stop into one rule
- do not use oracle truth in any trigger
- do not claim broad generality from the first small panel

## Most likely next step if the first pass is promising

A second-pass calibration on a somewhat broader panel, still offline, adding:

- one or two more fresh-seed hard p9 runs
- one more solved/medium control family
- better Stage 3.5 work-unit savings proxies when progress files exist

## Bottom line

The v2 experiment should try to prove something modest but valuable:

- that there exists a **family-aware dump/stability signal** worth further
  investigation

That alone would already make later stop-policy work much more grounded.
