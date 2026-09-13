# Execution core

The core materialises the validated public request and binds the runtime
components used by one solve.

It owns the internal configuration, problem/evaluation boundary, engine
orchestration, shared types and capability contracts.

Normal callers reach this through `api.run`.

The runtime configuration is an execution representation of the public request,
not another user-facing configuration layer.

See [Architecture](../../../docs/architecture/README.md) and
[Run pipeline](../../../docs/architecture/pipeline.md).
