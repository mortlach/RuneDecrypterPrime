# How-To: Run a Deterministic Solve

Audience: Hands-on
Time: 3-5 minutes
Outcome: Reproduce a seeded run and compare telemetry
Prereqs: Python 3.11+, repo installed (`pip install -e .[dev]`)

## Hands-on
1. Follow the quickstart steps (virtualenv, `pip install -e .[dev]`).
2. Run a tutorial with `--print-progress` and keep the default seed.
3. Compare `output/tutorials/<run>/logs/app.jsonl` with another solver's run; `telemetry.run.seed` should match.

## Expert
1. Configure RunAPI with explicit `seed`:
   ```python
   from rune_decrypter_prime.api import run, SolverSpec, KeySpec, by_name
   sol = run(
       text="??????",
       cipher=by_name.cipher("vigenere", key_len=6),
       key=KeySpec.repeat(len=6),
       solver=SolverSpec.ga(seed=1337, progress_pct=1),
       telemetry_on=True,
   )
   ```
2. Log outputs land in `output/tutorials/...`; archive META.json + logs when sharing results.
3. For tests, run `pytest -m tier_a` to ensure determinism across GA/SA/Hybrid tutorials.

## Troubleshooting
- If seeds differ, re-check environment variables and tutorial constants.
- Use `docs/guides/troubleshooting.md` for a checklist.

