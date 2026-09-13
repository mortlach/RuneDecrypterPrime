# Architecture overview

RDP uses one typed public boundary over the runtime components:

```text
from rdp import api
        |
        v
     RunSpec
        |
        v
validation and input preparation
        |
        v
cipher + key operations + solver + scoring
        |
        v
    RunResult
```

The public request says what experiment should be run.

The implementation owners decide how their part of that experiment works.

## Public layer

Normal user code starts with:

```python
from rdp import api
```

A solve is described with `RunSpec`:

```python
request = api.RunSpec(
    problem_input=problem_input,
    cipher=cipher,
    key_space=key_space,
    solver=solver,
)

result = api.run(request)
```

Known-key work uses `api.encrypt(...)` and `api.decrypt(...)`.

See [API reference](../reference/README.md).

## Component ownership

The major pieces remain separate:

- ciphers define the cipher relation
- key operations define valid key structure and changes
- solvers search the allowed space
- scoring ranks candidate plaintexts
- data modules provide source material such as Liber Primus
- telemetry records execution behaviour
- result and artifact code report what happened

The ownership boundary also keeps the cryptanalytic assumptions separate. A
solver change does not need another cipher or scoring model around it.

See [Project aims and design principles](../project_overview.md).

## Validation before execution

Public requests are typed and validated before the engine runs them.

Invalid combinations should fail clearly rather than being silently adjusted.

The same principle applies to requested assets and scoring capabilities.

A reported run should therefore correspond to the configuration that was
actually requested, or clearly report an authorised difference.

## Requested and effective state

Some execution details are resolved at runtime.

RDP records the effective configuration, stop reason, solver and scorer reports,
reproducibility information and telemetry in `RunResult`.

See [Reading a result](../guides/results.md) and
[Telemetry](../guides/telemetry.md).

## Extension

New behaviour extends the component that owns it.

A new cipher becomes a cipher.

A new search method becomes a solver.

A new source becomes part of the data layer.

A new ranking signal becomes scoring evidence.

The implementation can grow without adding another public route.

See [Extending RDP](../guides/extending_rdp.md) and
[Development](../development/README.md).
