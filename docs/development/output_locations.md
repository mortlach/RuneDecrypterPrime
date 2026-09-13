# Output locations

For normal solving, choose the output location explicitly in `LoggingConfig`
when the default is not suitable.

```python
from pathlib import Path
from rdp import api

logging = api.LoggingConfig(
    output_root=Path("my_runs"),
    run_category="solve",
    label="period7",
)
```

Attach that configuration to the run:

```python
request = api.RunSpec(
    ...,
    logging=logging,
)
```

A source checkout otherwise uses its normal `output/` area.

`run_directory` can be used when a run must use one exact directory.

If the selected destination cannot be used, the run fails rather than silently
writing somewhere unrelated.

See [Outputs](../guides/outputs.md) for when a run needs files and
[Logging parameters](../reference/parameters/logging.md) for the complete
configuration.

Telemetry does not require an output directory. See
[Telemetry](../guides/telemetry.md).
