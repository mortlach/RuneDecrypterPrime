# How-To: Benchmark Solvers (CPU)

Audience: Hands-on / Expert
Time: 3–6 minutes
Outcome: Run a small, deterministic benchmark and capture results under output/
Prereqs: Python 3.11+, repo installed (pip install -e .[dev])

## What you run
- A tiny CPU-only harness that compares a few presets on short texts.
- Seeds are fixed; telemetry is disabled for speed; outputs are archived under output/tools/benchmarks/.

## Run it
```powershell
# From repo root
python tools/benchmarks/benchmark_harness.py
```
You will see a CSV table in the console and an archive folder printed, e.g.
`[bench] Reports written to output/tools/benchmarks/20250101T120000Z__bench__abcd123`.

## Outputs\n- results.json � list of rows (name, score, seconds)
- results.csv – name,score,seconds
- results.json – the same rows in JSON

## Tips
- Keep benchmarks on CPU to compare apples with apples across machines.
- Use the same seed when you tweak budgets; seconds should be stable within noise.
- If a code change adds many redundant array conversions, seconds will drift – use this harness to catch regressions.

## Related docs
- guides/outputs.md
- guides/solvers_deep.md



## Compare two runs
`powershell
python tools/benchmarks/compare_runs.py <old.json> <new.json>
`
A slowdown >20% is flagged for quick triage. Keep budgets tiny and CPU-only for consistent comparisons.

## Run all tutorials (timed)
`powershell
python tools/benchmarks/run_all_tutorials.py
`
Writes tutorials_results.json/csv under output/tools/benchmarks/... and exits non-zero if any tutorial fails to run.

## Profile code paths (cProfile)
`powershell
# All canonical tutorials, top 30 functions
python tools/benchmarks/profile_bench.py --target all --top 30

# A single tutorial module
python tools/benchmarks/profile_bench.py --target tutorials.v1.Tutorial_MonoSubstitution_GA --top 50
`
Outputs include raw .prof, a human-readable top-N, and a JSON top-N plus per-category cumulative time under output/tools/benchmarks/... .
