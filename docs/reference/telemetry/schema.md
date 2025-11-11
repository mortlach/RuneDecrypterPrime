# `telemetry/schema.py`

> Purpose: small helper module that converts enums/objects into canonical strings before telemetry is emitted. Keeps JSON outputs consistent across platforms.

## Functions
- `to_canonical_device_str(dev)` - Normalises `Device` values or strings to `"cpu"` / `"cuda"`.
- `to_canonical_impl_str(impl)` - Converts scorer implementation enums/strings to lowercase tokens (e.g., `"numpy"`, `"torch"`, `"auto"`).

## Usage
Called by `core/engine/engine.solve` and `telemetry/events.py` when building `run_start`/`run_end`/solver payloads.

## Tests
- `tests/telemetry/test_schema_contract.py` - asserts the output uses the canonical device/impl tokens defined here.

## Related Docs
- `docs/reference/telemetry/events.md` - consumers of these helpers.
- `docs/reference/core/types.md` - upstream validators that produce the enums passed into this module.

