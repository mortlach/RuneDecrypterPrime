# Cipher-development campaign template

Copy only the sections and files that have a real purpose. This is a starting checklist, not a campaign engine.

## Suggested minimal directory

```text
cipher_development/<campaign>/
  CAMPAIGN.md
  config.py
  benchmark.py
  search.py
  run.py
```

A smaller campaign is preferable when it remains readable.

## Required campaign brief sections

- Problem
- Fixed benchmark or real-problem contract
- Known RDP contracts
- Evidence mode
- Truth policy
- Applicable prior lessons
- Intentional departures from those lessons
- Current failure classification
- Closed mechanisms
- Scientific question
- Hypothesis
- Strongest alternative
- Candidate identity
- Candidate archive policy
- Replay plan
- Decision rule
- Latest result
- Current candidate archive status
- Next experiment
- Candidate lessons awaiting promotion

## Required implementation-task fields

- Files allowed to change
- Files forbidden to add
- Exact question
- Expected tests
- Expected artifacts
- Budget
- Stop criteria
- Required implementation report

## Explicit configuration

```python
RUN_PROFILE = "canary"
MASTER_SEED = 101
```

Do not use argparse or environment variables for campaign configuration. Record material solver and scorer settings explicitly. Do not place plaintext truth, known keys or oracle metrics in execution configuration.

## Minimal runner shape

```python
from pathlib import Path


def run_campaign(repo_root: Path):
    case = build_case()
    spec = build_experiment_spec()
    with ExperimentRun(spec=spec, configuration=CONFIGURATION, repo_root=repo_root) as run:
        outcome = run_search(case)
        artifacts = write_artifacts(run.run_dir, outcome)
        return run.finish(
            decision=declared_decision(outcome),
            stop_reason="max_rounds",
            result_summary={"artifacts": artifacts},
        )
```

Keep control flow campaign-local. Do not add generic numbered stages, solver inheritance, automatic registration or plugin loading.

## Replay plan

A replayable campaign persists:

```text
artifacts/replay_context.json
candidate archive or replay batch
artifacts/experiment_manifest.json
artifacts/experiment_result.json
```

The replay context contains only search-visible information required to reconstruct evaluation. It must not contain benchmark truth. Replay verifies or reranks saved candidates; it does not rerun discovery or exploitation.

## Milestone synthesis

Generate a milestone synthesis after a meaningful group of runs, not after every run. Select run IDs explicitly. Review the generated JSON and Markdown together with raw artifacts, then update `CAMPAIGN.md` and `LESSONS.md` manually.
