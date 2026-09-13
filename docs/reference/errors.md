# Public errors

RDP exposes six stable top-level error types.

| Error | Meaning |
| --- | --- |
| `RdpError` | Base class for stable public RDP failures. |
| `ConfigurationError` | Invalid public configuration. May include a field path and capability issues. |
| `CapabilityUnavailableError` | A requested capability cannot run. Carries `RunStatus` and capability issues. |
| `AssetUnavailableError` | Required asset is unavailable. A specialised capability error. |
| `NonInvertibleCipherError` | Known-key encrypt/decrypt was requested for an unsupported cipher operation. |
| `ExecutionError` | Failure during execution. Carries status, phase and optional context. |

Ordinary validation can also raise Python `TypeError` or `ValueError` at the
public boundary when a field has the wrong type or violates a direct value
constraint.

## Catching an RDP error

The stable errors are available from `api`:

```python
try:
    result = api.run(request)
except api.ConfigurationError as exc:
    print(exc)
```

A caller that wants one catch for the stable RDP hierarchy can use:

```python
try:
    result = api.run(request)
except api.RdpError as exc:
    print(exc)
```

Direct type and value mistakes can still raise `TypeError` or `ValueError`, so
configuration should be corrected rather than treated as a recoverable solver
failure.

The project avoids silently changing invalid requests. See
[Project aims and design principles](../project_overview.md).

For common configuration mistakes, see
[Troubleshooting](../guides/troubleshooting.md).
