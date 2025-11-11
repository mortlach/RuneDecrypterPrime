# Writing Tests (patterns)

## API determinism

- Run twice with the same inputs/seed and assert the same `best_key`, `best_score`.
- Verify `Solution` structure and types.

## Cipher contracts
- Round‑trip encrypt/decrypt.
- Key Normal Form validation (permutation bijection, vector modulo‑29).

## Solver contracts
- `evals` strictly increases; `since_improve` resets on improvement.
- No global RNG calls on execution paths (mock or inspect).

## Telemetry invariants
- `META.json` has `seed`, `device`, `solver` and a pipeline block.
- Hybrid phases appear in order.

