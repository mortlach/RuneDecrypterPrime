# Uniform runner / stage engine reference — 2026-04-09

Status: active
Work status: done
Project: benchmark_campaign_v1_1

This note preserves a broader future-architecture idea and its grounded review.

## Preserved legacy files

- `nowli_imrpovements_refactor_for_benchcamp.txt`
- `nowli_imrpovements_refactor_for_benchcamp_review.txt`

## Why they are worth keeping

Together these files capture something more useful than a random draft:

### A. The proposal contributes
- a serious long-term direction:
  - one campaign runner
  - one stage engine
  - one adaptive policy interface
- explicit no-WLI-first thinking
- span-hamming integrated as a first-class cost-aware part of the pipeline
- a bridge between benchmark campaigns and solver architecture

### B. The review contributes
- a grounded explanation of where that direction already aligned
- a grounded explanation of where it conflicted with locked v1.1 contracts
- concrete evidence references into current code/docs

## Why this belongs here

This is not active no-WLI planning, and it should not replace the live benchmark
pack.

It is better treated as:
- future-architecture reference
- useful design direction
- historical review context

That makes the broader benchmark/p13-learning home a better fit than the
downstream `5455` thread pack.
