# Outputs and artefacts

The first thing to know is that `api.run` does not need a directory in order to
return a result. An ordinary run returns a typed `RunResult` in memory.

Disk output starts when you supply `api.LoggingConfig`, or when a repository
tool such as the installer or tutorial runner deliberately writes its own
evidence.

## A normal API run

Without logging:

```python
from rdp import api

result = api.run(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=8, rounds=2, seed=7),
)
```

`result` contains the recovered plaintext/key when available, score, run status,
solver/scorer reports, configuration evidence, reproducibility metadata, oracle
information and telemetry. No run directory is requested by this call.

## Requesting a run directory

Supply a logging configuration when you want on-disk run evidence:

```python
from rdp import api

logging = api.LoggingConfig(
    run_category="solve",
    label="trial",
    write_solver_report=True,
    write_display_summary=True,
    write_artifact_manifest=True,
)
```

When logging is initialised, RDP creates a unique directory beneath the selected
output root:

```text
<output-root>/
  <run-category>/
    <run-id>/
      META.json
      config/
        logging.json
      logs/
      trace/
      artifacts/
```

`META.json` and `config/logging.json` are written when the run directory is
created. The optional switches control additional output:

- `write_event_log` enables the structured event log;
- `write_solver_report` writes `artifacts/solver_report.json`;
- `write_display_summary` writes `artifacts/rdp_display_summary.json`;
- `write_artifact_manifest` writes `artifacts/run_artifacts_manifest.json`.

The report files are review/share artefacts. The display summary is not a
solver-state resume file.

## Choosing the output root

The first applicable destination wins:

1. `LoggingConfig.output_root`;
2. the absolute `RDP_OUTPUT_ROOT` environment variable;
3. `output/` in the RDP source checkout;
4. for an installed package without a source checkout, the operating system's
   per-user `RuneDecrypterPrime` data directory with an `output/` child.

An invalid or unwritable selected location fails. RDP does not silently choose
somewhere else.

`LoggingConfig.run_directory` can select the run directory more precisely. An
absolute value is used directly; a relative value is placed beneath
`<output-root>/<run-category>/`.

See [output locations](../development/output_locations.md) for the developer
case, including multiple checkouts and external output roots.

## Installer, tutorials and validation tools

Repository tools also write evidence, but they do not all pretend to be normal
`api.run` directories.

With the default source output root:

- `python install.py` writes under `output/install/<run-id>/`;
- the tutorial runner stores captured subprocess output under
  `output/tutorial_logs/`;
- CI and validation tools use their documented categories such as
  `output/ci_logs/` and `output/test_logs/`.

Use each tool's README or validation page for its exact evidence. There is no
benefit in inventing one giant directory diagram and then requiring every tool
to impersonate it.

## Portable output and sharing

`LoggingConfig.portable_output` defaults to `True`. Public metadata therefore
uses portable paths and redacts machine/user identity by default.

That does not make arbitrary raw logs anonymous. A traceback or subprocess log
can still contain a local path supplied by another program. Review raw logs
before sharing them.

Generated output is evidence, not source code. Keep it out of the maintained
source tree.
