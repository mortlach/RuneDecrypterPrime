# How-To: Run a Deterministic Solve

Audience: Hands-on
Time: 3-5 minutes
Outcome: Reproduce a seeded run and compare telemetry
Prereqs: Python 3.11+, bootstrap complete (`python install.py`)

## Hands-on
1. Follow the quickstart steps and run `python install.py`.
2. Run `python tutorials/v1/run_pretty_print_release.py`.
3. Compare the tutorial logs under `output/tutorial_pretty_print_logs/` with another run.

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
- If seeds differ, re-check tutorial constants in the runner file.
- Use `docs/guides/troubleshooting.md` for a checklist.


