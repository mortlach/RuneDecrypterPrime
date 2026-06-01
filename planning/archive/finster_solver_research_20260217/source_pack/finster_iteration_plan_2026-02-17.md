# Finster Solve Iteration Plan (Research-Only)

Date: 2026-02-17  
Scope: `solving/finster/solve_runic_a.py` through `solve_runic_e.py` and alignment with RDP solver stop controls.

## Goal

Implement the 7 agreed control ideas in a way that:

1. prioritises the most likely cipher/period/columns first,
2. prevents runaway runtime,
3. keeps strong candidates for deeper follow-up,
4. produces clear reasoned logs for every stop/skip decision.

No code changes in this step. This document is the implementation plan.

## What already exists (baseline)

Current scripts already include useful pieces:

- Most-likely-first stage order:
  - `baseline_sub` -> `product_periodic_columnar` -> `product_followup` -> optional `baseline_vig`
- Per-attempt progress and ETA:
  - `plan[...]`, `progress=...`, `stage_progress=...`, `elapsed`, `eta`
- Solver-level stop controls already used:
  - `stop_score`, `plateau_rounds`, `plateau_min_delta`
- Stop reason extraction and logging:
  - `stop_reason` from solver/run telemetry
- Candidate follow-up:
  - in-memory `product_candidates` + `_pick_promising_candidates(...)`
- Run artifacts:
  - `preflight.json`, `config.json`, `runs.csv`, `best.json`, `console.log`

Main gap: these controls are mostly local/per-attempt. We still need global budgeting, resume, persistent candidate queue, and report-grade summaries.

## Run-Evidence Update (runic_a, 2026-02-17 04:15 local)

Observed from live run:

- `baseline_sub` is expensive even with one period:
  - ~236s to ~328s per seed
  - ~126k to ~184k evals per attempt
  - exits mostly via `no_improve_260`
- Current threshold `STOP_IF_SCORE_GE=0.03` is too permissive for current scorer:
  - observed `pct_lm` already around 0.11 to 0.12 in early baseline runs
- Current upper-bound plan (`sub=5`, `prod=60`, `follow=8`) means Stage B dominates runtime.

Plan impact:

- Keep the same 7 ideas, but reprioritise implementation to reduce Stage B spend earlier.
- Add explicit Stage B pruning defaults in first implementation batch.
- Move scout/deepen earlier in rollout (immediately after hard budgets).

## Principle

Use existing RDP controls as the inner loop stop mechanism (`stop_score`, `plateau_rounds`).  
Add outer orchestration controls in `solve_runic_*.py` for run-level governance.

## Idea 1: Hard Budget Guards

### Problem

A run can still consume too much wall-clock or too many attempts/evals before outer logic stops it.

### Plan

Add run-level budget config keys:

- `MAX_TOTAL_SECONDS`
- `MAX_TOTAL_ATTEMPTS`
- `MAX_TOTAL_EVALS`
- `MAX_STAGE_SECONDS` (dict by stage)
- `MAX_STAGE_ATTEMPTS` (dict by stage)

Enforcement points:

- before dispatching each `run(...)` call
- immediately after each attempt via `_record(...)`

If guard trips:

- emit explicit stop line:
  - `RUN_END reason=budget:<type>`
  - stage-level: `stage-stop reason=budget:<type>`
- write partial outputs as normal (`runs.csv`, `best.json`, plus summary report in Idea 7).

### Acceptance

- Run cannot exceed configured total budget by more than one in-flight attempt.
- Every budget termination has a machine-readable reason string.

## Idea 2: Resume Mode

### Problem

Interrupted runs restart from scratch and lose momentum.

### Plan

Add `RESUME_MODE=True/False` and `RESUME_FROM=<latest|path>`.

State files:

- `state.json` checkpoint after every attempt
- append-only `candidate_queue.jsonl` (Idea 5)

Resume behavior:

- load previous `runs.csv` and `state.json`
- reconstruct completed attempt keys:
  - `(seed, stage, cipher, period, columns, order)`
- skip already-completed attempts
- restore best trackers:
  - `best_sub_*`, `best_prod_*`, stage counters, attempts/evals/time totals

### Acceptance

- Killing and restarting continues from next untried attempt.
- Replayed run does not duplicate completed rows.

## Idea 3: Scout -> Deepen Schedule

### Problem

Current schedule is better than before but still spends heavy compute before full global ranking.

### Plan

Two-pass orchestration:

Pass 1 (`scout`):

- low-cost solver configs with strict plateau:
  - small `steps/restarts`, low `top_k`
- evaluate broad candidate grid quickly
- store normalized rank metric:
  - primary: `pct_lm`
  - fallback: score

Pass 2 (`deepen`):

- take top `K` unique tuples from scout:
  - `(seed, period, columns, order, cipher_family)`
- rerun with heavier configs:
  - existing `PROD_SOLVER` / `PROD_FOLLOWUP_SOLVER` style
- keep using solver-level `stop_score` and `plateau_rounds`

Immediate pruning defaults (from latest run evidence):

- Stage B candidate reduction before heavy runs:
  - keep top `2` seeds from Stage A + `1` wildcard seed
  - test columns `[3,4,5]` first
  - unlock `[2,6,7]` only if no candidate crosses a promotion threshold
  - test one order variant first, run second order only for promoted candidates
- Promotion threshold policy:
  - avoid fixed low threshold `0.03` for current scorer
  - use either:
    - dynamic threshold based on Stage A distribution, or
    - stricter temporary fixed threshold around observed scale (for current run family)

### Acceptance

- Broad grid coverage occurs before heavy spends.
- Deepen set is explicitly logged and explainable.

## Idea 4: Diminishing-Returns Stop (Outer Loop)

### Problem

Solver plateau stops apply within attempts, but whole-run progress can still stagnate.

### Plan

Add global stagnation tracking across attempts:

- `GLOBAL_STALL_MIN_DELTA`
- `GLOBAL_STALL_WINDOW_ATTEMPTS`
- `GLOBAL_STALL_WINDOW_SECONDS`

Track rolling best metric and stop run when no material improvement across configured window.

Stop reason examples:

- `budget:global_stall_attempts`
- `budget:global_stall_time`

### Acceptance

- Long flat runs terminate with explicit stall reason.
- Strongly improving runs do not false-stop.

## Idea 5: Persistent Best-Candidate Queue

### Problem

Promising candidates are currently in-memory and limited to current run.

### Plan

Create persistent queue file under each output folder:

- `candidate_queue.jsonl`

Entry fields:

- rank metric (`pct_lm`, score)
- stage, seed, period, columns, order
- key (if available)
- stop reason
- source run id + timestamp

Queue policy:

- dedupe by `(cipher, seed, period, columns, order, key_hash)`
- maintain top-N per stage and top-N global
- feed `product_followup` and future resumes from this queue first

### Acceptance

- Restarted runs can continue deepening prior best candidates.
- Queue is auditable and reproducible.

## Idea 6: Run Profile Presets

### Problem

Too many knobs are manually edited; inconsistent across `runic_a..e`.

### Plan

Define named profiles with explicit budgets/solver configs:

- `smoke`
- `quick`
- `balanced` (default)
- `deep`

Selection:

- `RUN_PROFILE` constant and optional env override

Profile controls:

- period/column limits
- stage solver configs
- global budgets
- scout/deepen K and thresholds

Apply uniformly across all five scripts to avoid drift.

### Acceptance

- Profile switch changes runtime scale predictably.
- Same profile semantics across `runic_a..e`.

## Idea 7: One-Page Summary Report

### Problem

Current outputs are detailed but not a single concise experiment report.

### Plan

Add `summary.md` + `summary.json` at run end.

Sections:

- run metadata (cipher id, profile, git sha, start/end times)
- planned vs executed attempts by stage
- budget usage (time/evals/attempts)
- stop reason counts
- top candidates table
- best-by-stage with preview snippets
- recommended next action:
  - resume/deepen/stop

### Acceptance

- A reviewer can understand outcome and next step without parsing raw logs.

## Integration with current start-of-iteration output

At `RUN_START`, print one compact configuration header:

- profile
- budgets
- scout/deepen policy
- period/column shortlist
- stage order

At each stage transition, print:

- planned attempts remaining
- active guardrails
- reason for any skip (e.g., threshold met, budget, resume dedupe)

At `RUN_END`, print:

- final reason
- attempts/evals/time
- pointer to `summary.md`, `summary.json`, `candidate_queue.jsonl`

## Rollout sequence (recommended)

1. Hard Budget Guards (Idea 1)
2. Scout->Deepen (Idea 3), including Stage B pruning defaults
3. Resume Mode (Idea 2)
4. Persistent Candidate Queue (Idea 5)
5. One-Page Summary Report (Idea 7)
6. Diminishing Returns Stop (Idea 4)
7. Profile Presets and cross-script standardization (Idea 6)

Rationale: first cap risk, then aggressively reduce expensive search branches, then add recoverability and reporting.

## Cross-script strategy (`runic_a..e`)

Current scripts are near-copy variants. To reduce divergence in the implementation phase:

- define shared orchestration helpers in one module (future code step)
- keep per-cipher files as thin config wrappers:
  - ciphertext filename
  - period priors
  - any cipher-specific exceptions

This makes all 7 ideas land once, then apply to all ciphers consistently.

## Validation checklist for implementation phase

- Same behavior with `RESUME_MODE=False` as today (backward compatibility)
- Budget stop reasons visible in both console and saved JSON/CSV
- Resume idempotence:
  - restart twice, no duplicate attempts
- Candidate queue stability:
  - dedupe works, top candidates preserved
- Profile runtime sanity:
  - `smoke < quick < balanced < deep` in total time
- Report completeness:
  - summary includes stop reasons, best candidates, next action
