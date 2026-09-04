# Architecture guide

RDP follows one execution path:

```text
typed RunSpec -> public validation -> problem materialisation -> engine
              -> solver and scorer -> typed RunResult
```

Public callers import `from rdp import api`. Internal callers import the exact
module that owns the implementation they need. The package has no generic
internal facade and no duplicate public implementation.

## Public request

`api.RunSpec` combines one typed input with immutable cipher, key-space and
solver specifications. Scoring, logging, direction, device, telemetry,
permutation and interruptor policy are explicit fields.

```python
request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.columnar(columns=4),
    key_space=api.KeySpec.permutation(length=4),
    solver=api.SolverSpec.beam_search(width=32, rounds=4, seed=5),
    text_direction=api.TextDirection.LEFT_TO_RIGHT,
)
result = api.run(request)
```

The component overload of `api.run` constructs the same request. It is a
convenience, not a second execution route.

## Engine ownership

The exact `rdp.ciphers`, `rdp.keyops`, `rdp.solvers`, `rdp.scoring`,
`rdp.telemetry`, `rdp.data` and `rdp.io` modules own engine behaviour. The
materialisation and execution path is owned by `rdp.core`.

## Determinism and reporting

Solver seeds are part of `SolverSpec`. Requested and effective configuration,
stop status, scorer capability, telemetry and artefact decisions are returned in
`api.RunResult`; truth or oracle data does not silently affect production
ranking.

Contributor changes must preserve exact ownership, typed public construction
and the single request-to-result path.
