# Organiser Guide (v1.1)

This guide is for the person coordinating the campaign.

## Inputs
You collect multiple `run_bundle/` folders from contributors.

## Step 1: Validate each run bundle (mandatory)
Run bundle validation against v1.1 requirements:
- schema validation
- campaign_id/git_sha match
- no duplicate job_id inside a bundle
- CPU-only compliance fields present
- status and stop_reason present and valid

Bundles that fail validation are rejected and must be rerun/fixed.

## Step 2: Combine results (dedupe)
Combine all valid results.jsonl into:
- combined_results.jsonl
- collisions.jsonl (duplicates recorded)

Use deterministic dedupe rules:
1) solved > non-solved
2) higher best_match_ratio
3) lower total_seconds
4) stable tie-break (runner_id then timestamp)

## Step 3: Aggregate
Generate:
- summary_by_cell.csv
- summary_by_profile.csv
- heatmaps (two orders)
- stop_reason_counts_by_cell.csv
- stop_reason_counts_by_profile.csv

## Step 4: Publish campaign artefacts
Publish a “campaign outputs bundle” containing:
- campaign config and profile catalogue used
- full manifest and shards
- combined_results.jsonl (+ collisions.jsonl)
- summary CSV outputs
- a short notes/changelog file
