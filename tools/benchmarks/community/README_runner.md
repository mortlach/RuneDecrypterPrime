# Runner Guide (v1.1)

This guide is for contributors running a shard.

## Step 1: Setup + preflight
Run the repository setup/deploy step (see docs/setup). It must produce:
- benchmark_ready.json
- preflight_report.json (pass)

If setup fails, do not run shards. Share setup/preflight logs for debugging.

## Step 2: (Recommended) Canary
Run the canary campaign first:
- small shard
- minutes to run
If canary fails, stop and share logs.

## Step 3: Run your shard
You will be given:
- a campaign bundle (config, profile catalogue, schemas)
- a shard manifest JSONL

You will create a small local runner config file using the template:
- tools/benchmarks/community/examples/runner_config_local.template.json

You should only edit:
- runner_id
- shard_path
- output_root
- resume
- (optional) max_jobs

The runner must:
- run in campaign mode (no proven autoskip)
- only skip jobs via resume (already recorded job_id)
- write results incrementally

Example command:

```powershell
python tools/benchmarks/community/run_shard.py `
  --runner-config tools/benchmarks/community/examples/runner_config_local.template.json `
  --campaign-config tools/benchmarks/community/examples/campaign_config_v1_1.json `
  --profile-catalog tools/benchmarks/community/profile_catalog_v1_1.json
```

## Step 4: Share output
Share the folder:
- run_bundle/

It must contain:
- results.jsonl
- run.log
- run_meta.json
- setup + preflight reports/logs
- copies of the shard manifest, campaign config, and profile catalogue
