# Tutorial: Crib Drag API (Vigenere)

> Tracks: **Hands-on** - run `tutorials/v1/Tutorial_CribDrag_API.py` to see how cribs seed beam search. **Expert** - learn how the API exposes crib helpers for custom workflows.

Audience: Hands-on / Expert
Time: 5-10 minutes (CPU)
Outcome: Seed beam search with cribbed keys; compare against unseeded run
Prereqs: Python 3.11+, repo installed (`pip install -e .[dev]`)

## Goal
- Use a known plaintext fragment (crib) to seed the key search for a Vigenere cipher.
- Demonstrate how `initial_keys` hook into RunAPI.

## Hands-on Steps
1. Open `tutorials/v1/Tutorial_CribDrag_API.py` (setup help: `guides/quickstart.md`).
2. Fill in `crib_text` with a short guess (for example, `" rune "`).
3. Run the script; it encodes the crib, generates candidate keys, and launches `SolverSpec.beam` with those seeds.
4. Compare recovered plaintext/score with a run that omits the crib to see the benefit.
5. Inspect `output/tutorials/<run>/logs/app.jsonl` to confirm telemetry captured the seeded keys (`telemetry.run.initial_keys`).

## Expert Notes
- Crib helpers live in the tutorial file (search for `make_crib_keys`).
- Beam solver implementation: `src/rune_decrypter_prime/solvers/beam.py`; seeding logic uses `initial_keys` inside `api/run.py`.
- Regression: `tests/tutorials/test_crib_drag_api.py` covers both the seeded and unseeded paths.
- Always keep `telemetry_on=True` so seeded runs remain auditable.

## Example Snippet
```python
from rune_decrypter_prime.api import run, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.core.types import Direction

crib_keys = [...]  # generated from the crib alignment
sol = run(
    text="<ciphertext>",
    cipher=by_name.cipher("vigenere", key_len=12),
    key=KeySpec.repeat(len=12),
    solver=SolverSpec.beam(beam_width=64, seed=777, progress_pct=1),
    initial_keys=crib_keys,
    encoding_dir=Direction.LTR,
    telemetry_on=True,
)
print(sol.best_plaintext, sol.score)
```

## Outputs & Troubleshooting
- Logs/trace/artifacts live under `output/tutorials/...` like other tutorials.
- If the crib is ignored, ensure it matches the encryption direction and key length.
- For general issues, follow `docs/appendices/high_school_troubleshooting.md`.


