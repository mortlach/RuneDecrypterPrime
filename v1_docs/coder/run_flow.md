# V1 Run Flow

Status: implemented

## Public route

```text
RawTextInput / RuneIndexInput / SourceReferenceInput
  -> RunSpec(CipherSpec, KeySpec, SolverSpec, ScoringConfig)
  -> api.run
  -> RunResult(SolverReport, ScorerReport, status, replay evidence)
```

`api.run` is the sole solving operation. It accepts either one positional
`RunSpec` or the typed component convenience overload. The two forms produce
the same immutable request before execution.

## Runtime route

```text
RunSpec
  -> source/input materialization
  -> runtime CipherConfig and SolverConfig
  -> ProblemSpec
  -> ProblemInstance
  -> DecryptionProblem
  -> EngineConfig
  -> solver
  -> internal Solution
  -> RunResult and SolverReport
```

The public package owns request validation, exact cipher/key binding, execution
routing, and result conversion. The engine packages retain their current AN3
ownership. Internal consumers use those exact modules; they do not route
through a generic API-internal facade.

## Determinism and evidence

The `SolverSpec.seed` is preserved in replay metadata. An omitted seed receives
the documented deterministic engine value. Requested and effective capability
states, stop reason, runtime diagnostic reason, oracle use, scorer report, and
artifacts are represented explicitly in the returned reports.

Truth/oracle data does not affect production ranking. Diagnostic-only signals
do not affect ranking, stopping, tie-breaks, or candidate selection.

## Known-key route

`api.encrypt` and `api.decrypt` validate a semantic `ConcreteKey`, materialize
the exact runtime cipher owner, and return immutable `RuneIndices`. They do not
return or expose the runtime cipher instance.
