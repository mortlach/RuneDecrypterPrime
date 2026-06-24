# Troubleshooting

This page covers the normal V1 install and tutorial path.

All paths below are relative to the repository root.

## Quick checks

Run these from the repository root:

```text
python --version
python install.py
python tutorials/v1/run_pretty_print_release.py
```

Use the same Python interpreter for all three commands. If you install with one
Python and run tutorials with another, imports and native extensions can fail in
confusing ways.

## Common issues

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `ModuleNotFoundError: rune_decrypter_prime` | The package was not installed for the Python you are using now. | Run `python install.py`, then run the tutorial command again with the same `python`. |
| Native extension import fails, such as `_fastlm` | Build tools or package build dependencies are missing or stale. | Run `python install.py` again and inspect the newest log under `output/install_logs/`. |
| A tutorial fails but most tutorials pass | That tutorial hit a real failure or missing asset. | Open the matching log in `output/tutorial_pretty_print_logs/` and check the tail printed by the runner. |
| Output appears somewhere unexpected | The command was run from a different working directory. | Change to the repository root and rerun the command. |
| Results differ between machines | Different Python/package state, assets, or code checkout. | Confirm `python --version`, rerun `python install.py`, and check that Git is on the expected branch. |

## Tutorial logs

The normal V1 pretty-print runner writes full tutorial output here:

```text
output/tutorial_pretty_print_logs/
```

Each active pretty tutorial gets one text log. The console stays compact unless a
tutorial fails.

For a review pass that echoes every captured tutorial printout to the console,
run:

```text
python tutorials/v1/run_pretty_print_output_review.py
```

## What to include in a report

Include:

```text
python --version
the command you ran
the full error text
the relevant output/tutorial_pretty_print_logs/*.txt file
the current Git branch and commit, if available
```

Do not include local private files or unrelated generated output.

## Related docs

- `docs/setup/installation.md`
- `docs/guides/quickstart.md`
- `docs/README.md`
