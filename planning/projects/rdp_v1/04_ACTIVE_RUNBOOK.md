# Active runbook

Status: active
Work status: in_progress
Project: rdp_v1

## Immediate goal

Use `rdp_v1` as the clean repo-level convergence home without needing the old
planning migration scaffolding.

## Reading order

1. front-door files
2. `10_governance/`
3. `20_active_plans/`
4. `30_architecture_specs/`
5. `40_supporting_reference/` only as needed
6. `95_evidence_snapshots/` only if direct proof is needed

## Safe next steps

1. keep the front-door pack small and stable
2. keep `RunSpec` / `SolverReport` wording honest
3. decide whether any secondary notes should later move further back into
   `planning_old/`
4. avoid letting support/reference notes become competing entry points

## What not to do yet

- do not reopen bulk legacy migration
- do not let the supporting-reference layer become the new front door
- do not try to solve every architecture question in one pass
- do not let historical source references under `planning_old/` turn back into
  live reading habits
