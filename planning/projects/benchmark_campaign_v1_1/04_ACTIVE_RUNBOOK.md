# Active runbook

Status: active
Work status: in_progress
Project: benchmark_campaign_v1_1

## Immediate goal

Use the new normalised `benchmark_campaign_v1_1` shape as the second model
active project home, without falling back to `planning/drafts/` as the working
surface.

Current migration read:
- the absorbed benchmark draft duplicates are retired
- the remaining old-draft residue is outside this home's owned truth boundary

## Reading order

1. front-door files
2. `10_contracts/`
3. `20_active_plans/`
4. `30_validation_and_setup/`
5. `40_supporting_reference/` only as needed
6. `95_evidence_snapshots/` only if direct proof is needed

## Safe next steps

1. keep the front-door pack small and stable
2. keep benchmark/campaign truth separate from repo-level v1 truth
3. keep future-method and legacy-method notes secondary
4. avoid letting reference bundles compete with the front door
5. use `planning_old/projects/benchmark_campaign_v1_1/` only for historical
   migration/archive context

## What not to do yet

- do not reopen bulk legacy migration
- do not let the supporting-reference layer become the new front door
- do not treat future-method references as active benchmark truth
- do not delete old draft files until each one is classified
