# Scoring and assets history map — 2026-04-09

Status: active
Work status: done
Project: rdp_v1

This note records older repo-level plans now preserved under the active
`rdp_v1` home as secondary history/guardrail notes.

## Promoted source files

- `planning/old/scorign_refactor_plan.txt`
- `planning/old/data_refactor_plan_assets_migration_draft.txt`

## Why they are worth keeping

### A. Scoring refactor plan
Useful because it captures:
- bounded JSON-safe `ScorerReport` shape
- one report-builder normalisation point
- additive sidecar reporting rather than solver-loop rewrite
- test-gated parity and safety framing

### B. Assets migration draft
Useful because it captures:
- assets-first heavy-data movement out of `src/.../data`
- manifest and preflight discipline
- repo-relative path / no absolute path persistence rules
- deterministic rebuild and guardrail expectations

## Current role

These notes are:
- useful repo-level history and guardrails
- still relevant to v1 convergence/release thinking
- not part of the main live entry pack
