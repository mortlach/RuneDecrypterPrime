# Troubleshooting

## Pip reports an externally managed environment

Some Linux distributions protect their system Python using PEP 668. If pip
refuses to install RDP, use another Python or an environment you manage.

If you deliberately want pip to override that protection, run:

```text
python install.py --break-system-packages
```

This permits pip to modify the externally managed Python installation. The
installer never chooses that override for you.

## The result is nonsense

Check the problem input first.

For numerical input, confirm that the rune indices and WLI belong to the same
text.

For Liber Primus data, reload the source through `api.liber_primus` rather than
carrying old arrays between experiments.

See [Ciphertext input](ciphertext_input.md),
[Word-length information](word_length_information.md) and
[Liber Primus data](../reference/liber_primus.md).

Then check the cipher, key space, text direction and scoring assumptions.

## The run finishes without recovery

Read the stop reason and solver report.

See [Reading a result](results.md).

If the search is still improving when it reaches its budget, a larger search
may be justified.

If nearby searches all fail in the same way, revisiting the cipher or key model
is usually more informative than increasing the same budget.

See [Solvers](solvers.md) and [Comparing solve experiments](working_a_solve.md).

## WLI changes the result

That is expected when the WLI lane is enabled.

Check that the WLI is aligned with the exact ciphertext, then compare the same
run with:

```python
scoring = api.ScoringConfig(
    wli_lane_enabled=False,
)
```

See [Scoring](scoring.md).

## Same seed, different result

Compare the whole request, including scoring, WLI, direction, initial keys,
interruptors and compute device.

Then compare the result configuration, reproducibility metadata and telemetry.

See [Repeating a run](reproducibility.md) and [Telemetry](telemetry.md).

## CUDA is available but the run uses CPU

CPU is the default.

Set:

```python
compute_device=api.ComputeDevice.CUDA
```

when CUDA is required.

See [CUDA setup](../development/cuda_installation.md).

## No run files were created

`RunSpec.logging` defaults to `None`.

Add `LoggingConfig` when files are needed.

See [Outputs](outputs.md).

## The result is hard to inspect

Use the standard display view:

```python
api.display.print_result(
    result,
    spec=request,
)
```

See [Displaying results](displaying_results.md).
