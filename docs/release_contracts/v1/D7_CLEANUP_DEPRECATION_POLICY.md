# D7 cleanup and deprecation policy

D7 is the V1 cleanup guardrail.

Cleanup must not silently change the V1 specification. Every cleanup or removal must be traceable to a ledger entry, a replacement path, tests, docs, and a rollback note.

## Allowed statuses

- `retain` — keep for V1.
- `deprecate_only` — document the newer path, but keep the old path working for V1.
- `remove_after_green` — removal is allowed only after named tests/docs are green.
- `removed` — code has been removed in the same patch that updates the ledger and tests.

## Non-negotiable rules

1. Do not remove public compatibility paths just because they look old.
2. Do not promote experimental/report-only features into V1 production scoring.
3. Do not allow requested scorer lanes to warn and disappear.
4. Do not delete traceability evidence.
5. Do not combine cleanup with new feature work.
6. Do not broaden V1 scope during cleanup.

## Initial cleanup decisions

- Keep `RunAPI.solve = run` for V1; it may be documented as legacy, but should not be removed yet.
- Remove NumPy/Torch requested-lane warning/disable paths only after D3/D4 tests are green.
- Keep n-gram Hamming as experimental/report-only only.
- Keep save/restore solving outside V1.
- Keep ScheduledStreamLookup aliases because they are tutorial/user-facing convenience names.

## Ledger

The machine-readable ledger is:

```text
docs/release_contracts/v1/v1_cleanup_deprecation_ledger.json
```

Every cleanup patch must update that ledger if it touches a tracked item.
