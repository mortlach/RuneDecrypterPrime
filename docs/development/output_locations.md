# Output locations for development

This page is for developers who need an external output root, multiple checkouts
or a fixed run directory. For ordinary run output, start with the
[outputs and artefacts guide](../guides/outputs.md).

## Output-root precedence

RDP's shared resolver uses the first applicable destination:

1. an explicit output root, such as `LoggingConfig.output_root`;
2. `RDP_OUTPUT_ROOT`, which must be a non-empty absolute path;
3. `output/` in the source checkout containing RDP;
4. when no source checkout is available, the operating system's per-user
   `RuneDecrypterPrime` data directory with an `output/` child.

Explicit `Path` values are resolved normally, so a relative
`LoggingConfig.output_root` is relative to the caller's current working
directory. `RDP_OUTPUT_ROOT` is deliberately stricter and must be absolute.

The selected root is created and checked for writability. Failure is reported;
RDP does not fall through to a different destination.

Source-checkout detection follows RDP's project manifest and package layout. It
does not depend on which directory the terminal happened to start in.

## Run directories

For logged API runs, the normal layout is:

```text
<output-root>/<run-category>/<run-id>/
```

`LoggingConfig.run_directory` can override the generated run ID:

- an absolute `run_directory` selects that exact directory;
- a relative `run_directory` is resolved beneath
  `<output-root>/<run-category>/`.

The run directory then receives `META.json`, `config/logging.json`, and the
`logs/`, `trace/` and `artifacts/` directories.

## Multiple projects or checkouts

For several checkouts, keep checkout, interpreter and output choices together
in an external launcher. Set one absolute `RDP_OUTPUT_ROOT` per project or job.

For example:

```text
workspace/
  checkouts/candidate-a/
  checkouts/candidate-b/
  environments/candidate-a/
  run_outputs/project-a/
  run_outputs/project-b/
```

Each child process inherits the correct project root. A run-level explicit
`LoggingConfig.output_root` still wins when one is intentionally supplied.

This is simpler than discovering output folders after the run and moving them
around. Files are much less mysterious when they are written to the right place
in the first place.

## Portability and privacy

`LoggingConfig.portable_output=True` is the default. Portable run metadata uses
relative or labelled external paths and redacts user/host identity.

Raw process output is different. External commands and tracebacks can still
print absolute machine paths. Review raw logs before sharing them.

Generated logs, review packs and private working notes belong outside the
maintained source tree whether or not Git happens to ignore them.
