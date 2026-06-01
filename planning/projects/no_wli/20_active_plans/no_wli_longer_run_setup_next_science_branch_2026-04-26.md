# no-WLI Longer-Run Setup for Next Science Branch

Date: 2026-04-26

Status:

- setup note active
- no runtime launched by this note
- waiting for a named science hypothesis and target cell

## Starting Point

The selector-checkpoint subtopic is closed:

- replay-family science claim:
  - provisionally supported on fixed `1111/search7001-7005`
- review packaging:
  - review-ready after provenance reconciliation
- live canary preparation:
  - semantic/provenance pass
  - filtered `7002` saved runtime
  - kept `7003` preserved the selected path
- longer kept-lane repeat:
  - saved valid auditable evidence
  - confirmed a kept-lane throughput caveat

This means future work should move back to science questions, not spend more
time refining exact kept-lane wallclock unless the next claim depends on it.

## Operating Rule For Longer Runs

For the next longer run, prioritize evidence validity over exact timing
precision:

- launch in a pop-out PowerShell window
- tee stdout/stderr to a repo-relative log under `planning/working/`
- emit progress while running
- use a generous hard cap, default `8h` unless the named cell justifies more
- stop only if the run clearly exceeds the written cap or loses useful evidence
- audit the completed bundle before interpreting the result

Do not spend extra setup time trying to predict wallclock exactly once the run
is comfortably inside the available session budget.

## Required Before Launch

Before launching the next longer science run, write or update the run-specific
plan with:

- question
- suspicion
- main alternative
- target fixture/search cell or microbatch
- exact code path / script
- hardcoded constants to use
- intended cap
- stop condition
- expected artefact layers
- extractor/audit path
- pass / hold / close decision rule

The target must not be one of the closed candidate lines unless the plan states
a new mechanism and a new decision gate.

## Current Candidate Guidance

Do not launch:

- another selector-checkpoint timing repeat
- another candidate2 family-aware-budget replay in the current form
- another candidate3 broad overnight replay batch
- a generic live-runtime matrix

Acceptable next shape:

- one consciously designed conditioned rule
- one new paradigm probe
- one independently complete cell or small microbatch
- one extractor/audit that can read partial output if the run is interrupted

## Longer-Run Readiness Checklist

Use this checklist before launch:

- retained wallclock reference refreshed or consulted
- output parent exists and resolves under repo root
- log parent exists and resolves under repo root
- launcher runs in a separate PowerShell window
- launcher tees to a repo-relative log
- run emits progress to screen/log
- cap and stop condition are recorded in the plan
- no CLI arguments are required
- branch/ref/target selections are hardcoded in source or plan files
- extractor can summarize completed or partial output

## Decision

The next action is to choose the next science hypothesis and target cell. After
that, prepare a run-specific script/launcher and start the longer run under the
rules above.
