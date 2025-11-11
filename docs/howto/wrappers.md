# How-To: Use By-Name Wrappers

> Tracks: Hands-on shows how to call canonical ciphers/solvers without digging through modules; Expert covers how to add new wrappers safely.

Audience: Hands-on / Expert
Time: 2-4 minutes
Outcome: Materialise ciphers/solvers via `by_name` and run a solve
Prereqs: Completed quickstart

## Hands-on Usage
- Import from `rune_decrypter_prime.api.by_name` to materialise supported ciphers and solvers with friendly names.
- Stick to tutorials listed in `docs/tutorials/*.md`; they already demonstrate the wrapper arguments.
- Example run (outputs land in `output/tutorials/<run>/...`):
  ```python
  from rune_decrypter_prime.api import run, SolverSpec, KeySpec, by_name

  sol = run(
      text="??????",
      cipher=by_name.cipher("vigenere", key_len=6),
      key=KeySpec.repeat(len=6),
      solver=SolverSpec.sa(sa_iters=2000, seed=1234, progress_pct=1),
      telemetry_on=True,
  )
  print(sol.score, sol.meta["telemetry"]["run"]["cipher"])
  ```

## Expert - Adding New Wrappers
1. Register the underlying implementation (`ciphers/registry.py`, `solvers/<name>.py`, or `keyops/` factories).
2. Update `src/rune_decrypter_prime/api/by_name.py` to expose `cipher("my_cipher", **params)` or `solver("my_solver", **params)`. Keep argument names consistent with docs.
3. Extend the relevant guide/tutorial so Hands-on readers know when to use the new wrapper.
4. Update `docs/reference/api/wrappers/*.md` with the new signature.

## Verification
- `pytest tests/ciphers/test_by_name_future_wrappers.py -k <name> -q`
- `pytest tests/api -k by_name -q` (ensures normalisers accept the new alias).
- Confirm telemetry shows the wrapper name in `telemetry.run.cipher` or `.solver_name` inside `output/tests/<run>/logs/app.jsonl`.

## Tips
- Wrappers should normalise shorthand arguments (e.g., `key_len` vs `key_length`) so tutorials remain concise.
- Avoid importing heavy modules at import time; define factories that run only when the wrapper is called.

