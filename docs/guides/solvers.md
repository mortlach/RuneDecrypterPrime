# Solvers – Practical Playbook

Audience: Expert (or motivated Hands-on)  
Time: 6–10 minutes  
Outcome: Know when to pick Beam/GA/SA/Hybrid, which knobs to tune, and how telemetry/progress buckets reflect what’s happening.  
Prereqs: Read the Architecture overview; run at least one tutorial.

---

## 1. Shared concepts
- **Seeds** – every solver consumes a NumPy `Generator` seeded by `SolverSpec.seed`. Keep the seed fixed when comparing strategies so score differences come from the algorithm, not randomness.
- **Budgets** – either set explicit `eval_budget`/`iters` or rely on solver-specific knobs (beam width, generations, temperature schedule). All solvers honour `progress_pct` (default 1%) and emit telemetry at each bucket.
- **KeyOps** – solvers never modify ciphers/scorers directly; they move through the key space using the deterministic operations supplied by KeyOps (mutate, recombine, etc.).
- **Telemetry** – `solver_progress` records `{pct, iter, evals, best_score, since_improve}`; `solver_spans` encapsulate each solver/stage with params and final reason.

---

## 2. Beam Search
- **When to use:** small-to-medium key spaces, strong heuristics, or when you need deterministic tie-breaks (e.g., demos, reproducible tutorials).
- **Knobs:** `beam_width`, `rounds`, `top_parents_factor`, `sample_per_parent`. Keep `progress_pct=1` so buckets map cleanly to percentages.
- **Behaviour:** maintains a breadth-limited frontier, expanding columns via KeyOps. Perfect for Vigenère/Columnar combos when you want stable output quickly.

---

## 3. Genetic Algorithm (GA)
- **When to use:** larger key spaces where exploration/exploitation balance matters (e.g., substitution, mixed ciphers).
- **Knobs:** `pop_size`, `generations`, `elite_frac`, `mut_prob`, optional `local_improve_iters`. When you want more deterministic runs, keep the seed and population constant and only vary one knob at a time.
- **Telemetry:** look for `solver_spans.ga` entries showing population stats and final best score. `solution.meta["work"]` separates decrypt vs. score timing so you can spot LM bottlenecks.

---

## 4. Simulated Annealing (SA)
- **When to use:** tight key spaces where small neighbour tweaks are meaningful (e.g., short repeats). Good for quick scans when GA feels heavy.
- **Knobs:** `sa_iters`, `sa_init_temp`, `sa_min_temp`, `sa_cooling`, `sa_reseed_interval`, rescue options (`sa_rescue_drop_abs`, `sa_rescue_drop_ratio`). Keep `progress_pct` small to see the temperature curve in telemetry.
- **Behaviour:** accepts worse moves with probability `exp(d / T)`; telemetry shows temperature + since_improve counters so you know if you need more iters.

---

## 5. Hybrid (Beam → GA → SA)
- **When to use:** complex ciphers or composites (e.g., Columnar + Vigenère) where you want a coarse search, population refinement, and final polishing in one run.
- **Knobs:** same as individual solvers, grouped into phases. Telemetry emits a span per phase so you can measure how long each stage takes and whether later stages actually improve the score.

---

## 6. Comparison workflow
1. **Keep seed, scorer, and cipher fixed.** Only change one solver at a time.
2. **Run the tutorial/test** you care about (e.g., `pytest tests/tutorials/test_mono_substitution.py -q`).
3. **Inspect telemetry:** compare `telemetry.solver_progress` curves and `solution.meta["work"]` to see which solver is spending time where.
4. **Record outputs:** each run lands under `output/tests/...` or `output/tutorials/...`; zip the folder to share reproducible evidence.

---

## Related docs & tests
- Docs: `guides/solvers_deep.md`, `guides/pipeline.md`, `howto/deterministic_run.md`.
- Tests: `tests/solvers/`, `tests/tutorials/`, `tests/telemetry/test_solver_pipeline_block.py`.
