# Repository validation

From a source checkout, using the Python environment where RDP is installed:

```text
python tools/run_validation.py
```

`RUN_SET = 'smoke'` checks the runner, executes the first known-key
tutorial, and verifies the first solved LP workbook. It takes seconds. Change
the constants at the top of `run_validation.py`; the script accepts no arguments.

The current configuration is `RUN_SET = 'all'` for the full supported selection.
Set `RUN_SET = 'p7c7'` for just the single prepared-start P7/C7 solve.
Set `DRY_RUN = True` to
write and print its plan without launching any subprocess jobs.

| Selection | Contents |
| --- | --- |
| Tests | Pytest under `tests/`, including full-asset tests, excluding the development/campaign paths listed below. |
| Getting started | All ten numbered files under `tutorials/v1/getting_started/`. |
| Examples | The 24 admitted examples in `EXAMPLES`, including robust recipes, full-asset crib examples and the single-start P7/C7 example. |
| Solving | All nine numbered `solving/solved_lp/` workbooks, individually. |

The full selection currently has 44 jobs: one pytest job and 43 individual
programs. Some programs are also covered by pytest; the standalone run checks
their actual entry points as well. A selected program is not a claim of a
passing result: failures are reported, including missing optional dependencies.

See [the complete file selection](validation_selection.md) for all included test
files, tutorials, examples, workbooks, and exclusions.

## Scope

The runner never selects `tools/robustness/` campaigns, `cipher_development/`,
`solving/attempts/`, or the two multi-hour qualification examples named in
`EXCLUDED_EXAMPLES`. The single-start P7/C7 warm-start example is explicitly
included despite the older tutorial catalogue's qualification grouping.
Pytest excludes `tests/cipher_development/` and the two
`tests/tools/test_cipher_solver_campaign*.py` files listed in `EXCLUDED_TESTS`.
Ordinary contract tests that inspect qualification definitions remain included;
they do not launch qualification campaigns. Full assets must already be installed.
Optional Torch/CUDA skips remain visible in pytest's JUnit report and summary counts.

To add an ordinary example, add its stem to `EXAMPLES`. To exclude a new
qualification program, add its stem and reason to `EXCLUDED_EXAMPLES`. An
unclassified or missing example blocks the runner before execution. Numbered
getting-started and solved-workbook files are discovered in their dedicated
directories. Add tests normally under `tests/` and update the catalogue test
when intentionally changing the number of standalone programs.

## Results

Every invocation creates a unique run directory under `OUTPUT_ROOT`, with:

- `summary.json`: source commit, dirty-file list, Python version, exclusions,
  commands, results, timings, and pending/not-run jobs;
- one UTF-8 `.log` per job, written as the subprocess emits output;
- pytest JUnit XML, including skipped-test details;
- per-job `_artifacts/` folders for generated native outputs.

The shared [output policy](../docs/development/output_locations.md) chooses the
base directory. Validation uses its `validation/` child unless `OUTPUT_ROOT`
in the script explicitly selects another destination. Every job receives an
absolute `RDP_OUTPUT_ROOT` pointing to its own artifacts directory. Outputs are
written there directly; existing checkout outputs are left in place.

A normal Ctrl+C stops the active process tree and records unfinished jobs.
The atomic summary and completed logs remain usable after interruption.

Each job runs in a fresh subprocess with the current interpreter, the checkout
as its working directory, and UTF-8 output. Ambient Python path overrides and
pytest plugin autoloading are disabled. Native library availability is unchanged.
The console reports starts, completions and a heartbeat every ten seconds.
`SHOW_JOB_OUTPUT = True` also streams subprocess output to the terminal while
preserving the complete per-job log. Set it to `False` for a compact console.

`STOP_ON_FAILURE = False` gathers independent failures in one run. Set it to
`True` to stop after the first failure. A failed command, missing pytest
evidence, or workbook without final solved evidence makes the suite fail.
Pytest skips are reported; an entirely skipped test run is not considered a pass.

There are no runner time limits, either per program or overall. The runner waits
for each program to finish unless you interrupt it. Existing test assertions and
example solver settings remain part of those programs; this runner does not
rewrite their semantics.
No campaign or review-pack generation is hidden in the runner.

## GPU verification

Run `python tools/run_gpu_validation.py` with the installed RDP interpreter.
It installs the output-routing dependency when needed, reuses a verified CUDA
Torch runtime or provisions a compatible official wheel, checks CUDA matrix
arithmetic, then runs routing/provisioning/runner tests and the files listed in
`GPU_TEST_FILES`. This includes Torch collection checks, input validation,
scorer objectives, hash helpers, probe-loop safety, full-text AVG, span Hamming,
CPU/CUDA parity, telemetry and the CUDA solver smoke test.

The GPU selection fails if any selected test skips. `gpu.json` records the
provisioning result and points to test evidence; per-command logs, JUnit and the
validation summary preserve failures. No full tutorial/example run is included.
The `gpu` selection in the general runner runs only these test files and assumes
CUDA is already provisioned. Neither route imposes a runtime limit.
