# How-To: Benchmark Solvers (CPU)

Audience: Hands-on / Expert  
Time: 3–6 minutes  
Outcome: Run a deterministic benchmark and capture results under `output/tools/benchmarks/`.  
Prereqs: Python 3.11+, bootstrap complete (`python install.py --target dev`), CPU reference environment.

---

## What the harness does
- Exercises a handful of solver presets on short texts.
- Uses fixed seeds and disables telemetry for speed.
- Stores CSV/JSON summaries plus optional cProfile data under a timestamped folder.

---

## Run the main benchmark
```powershell
# From repo root
python tools/benchmarks/analysis/benchmark_harness.py
```
You’ll see a table in the console and a line like:
```text
[bench] Reports written to output/tools/benchmarks/20250101T120000Z__bench__abcd123
```

### Outputs
- `results.csv` – columns: name, score, seconds.
- `results.json` – same rows as JSON (easier to diff or feed into scripts).

Keep CPU-only runs for apples-to-apples comparisons across machines.

---

## Compare two runs
```powershell
python tools/benchmarks/analysis/compare_runs.py <old.json> <new.json>
```
The script flags slowdowns >20 % so you can triage regressions quickly. Use the JSON files from the benchmark folders.

---

## Run all tutorials (smoke + timing)
```powershell
python tools/benchmarks/analysis/run_all_tutorials.py
```
Writes `tutorials_results.csv/json` under the same benchmark folder and exits non-zero if any tutorial fails.

---

## Profile hot paths (cProfile)
```powershell
# All canonical tutorials, report top 30 functions
python tools/benchmarks/analysis/profile_bench.py --target all --top 30

# Single tutorial
python tools/benchmarks/analysis/profile_bench.py --target tutorials.v1.Tutorial_MonoSubstitution_GA --top 50
```
Outputs include `.prof` files, human-readable summaries, and JSON reports so you can compare cumulative times per category.

---

## Tips
- Keep seeds + budgets fixed so seconds stay within normal jitter.
- If you’re testing CUDA/Torch changes, run a separate GPU-focused harness; keep this CPU suite stable for reference numbers.
- When timings drift unexpectedly, inspect the benchmark folder’s `results.json` and rerun with `--top` profiling to see which functions changed.

---

## Related docs
- `docs/guides/outputs.md` – explains the output tree (`output/tools/benchmarks/...`).
- `docs/guides/solvers_deep.md` – deep dive into solver configs/patience knobs.
