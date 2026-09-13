# FAQ

## Does RDP need a GPU?

No. CPU is the default.

CUDA is useful for supported workloads on a suitable NVIDIA GPU, but it is a
choice made by the run.

See [CPU, CUDA and scoring](setup/scorer_backend_selection.md).

## What ciphertext input forms are supported?

For a normal `RunSpec`, RDP has two public input types:

- `RuneInput` for inferred or explicitly tagged text and rune indices
- `SourceReferenceInput` for a registered source such as Liber Primus

See [Ciphertext input](guides/ciphertext_input.md).

## Does a finished run mean the cipher is solved?

No.

A solver can finish normally because it used its search budget or met a stopping
condition. Recovery is a separate question.

See [Reading a result](guides/results.md).

## Why did two runs differ?

Compare the whole run: input, cipher, key space, solver settings, seed, scoring,
WLI, text direction, starting keys and compute device.

See [Repeating a run](guides/reproducibility.md).

## Where are the Liber Primus texts?

Use the `api.liber_primus` namespace. It can load named sources, transcript
sections, page spans, locators and partition entries.

See [Liber Primus data](reference/liber_primus.md).

## How do I see what happened during a run?

`RunResult` contains the solver report, scorer report, effective configuration,
reproducibility information and telemetry.

For a formatted view:

```python
api.display.print_result(
    result,
    spec=request,
)
```

See [Reading a result](guides/results.md),
[Displaying results](guides/displaying_results.md) and
[Telemetry](guides/telemetry.md).

## How do I save a run?

Add `LoggingConfig` to `RunSpec`.

A plain run otherwise remains in memory.

See [Outputs](guides/outputs.md).

## How do I add a new cipher or solver?

Start with [Extending RDP](guides/extending_rdp.md).

Focused cipher investigations belong in
[Cipher development](development/cipher_development.md).

Production contributor routes are in [How-to guides](howto/README.md) and
[Contributing](../CONTRIBUTING.md).
