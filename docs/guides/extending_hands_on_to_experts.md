# Extending RDP - Hands-on to Expert

> Tracks: **Hands-on** sections describe tinkering inside `tutorials/`; **Expert** sections show when and how to graduate changes into the core package.

Audience: Hands-on / Expert
Time: 8-12 minutes
Outcome: Promote prototypes into stable components with tests and telemetry
Prereqs: Ran at least one tutorial, basic pytest familiarity

## Overview
This guide maps the learning ladder:
1. **Hands-on** - build or tweak a cipher in `tutorials/` without touching core.
2. **Builder** - promote stable ideas into `src/rdp/ciphers/`, `keyops/`, or `api/`.
3. **Expert** - add new solvers or scoring backends with full telemetry/tests.

---

## Why Follow the Ladder?
- Keeps Hands-on experiments isolated and deterministic.
- Prevents half-finished ideas from destabilising the core pipeline.
- Makes it easy to review contributions because every rung has explicit entry/exit criteria and tests.

---

## Stage 1 - Hands-on Tutorials (safe sandbox)
**What you do:**
- Create a folder under `tutorials/v1/dev/` (e.g., `rail_fence/`).
- Implement encrypt/decrypt helpers plus a small brute-force search.
- Keep all randomness seeded (use `numpy.default_rng(seed)` and pass `seed` into any solver).

**How to use it:**
- Run the script with your preferred workflow (for example: `python tutorials/v1/dev/rail_fence/solve.py`).
- Log outputs will still go to `output/tutorials/...`, so other solvers can compare runs.

**When you're done:**
- Document the tutorial in `docs/tutorials/DEV_<name>.md`.
- Optional: add a recipe in `docs/howto` if it teaches a general lesson.

---

## Stage 2 - Promote to Core Cipher / KeyOps
**Requirements:**
- Cipher has deterministic encrypt/decrypt, supports key normal form, and passes round-trip tests.
- Includes KNF checks, scoring sanity, and telemetry coverage.

**Steps (Expert):**
1. Move the implementation into `src/rdp/ciphers/<name>.py`.
2. Register it with the existing runtime registry and, if the family is approved
   for the public surface, add the exact typed `api.CipherSpec` constructor.
3. Add tests:
   - `tests/ciphers/test_<name>.py` for round-trip + KNF.
   - Update tutorials or create a new one referencing the promoted cipher.
4. Update docs: mention the new cipher in `docs/guides/architecture.md` and relevant tutorials.

**Validation:** `pytest tests/ciphers -q` plus the telemetry contract.

---

## Stage 3 - Add / Extend Solvers
**Requirements:**
- Clear motivation (coverage gap, performance improvement).
- Deterministic RNG usage, telemetry spans, and `solution.meta["work"]` updates.

**Steps (Expert):**
1. Subclass `solvers/solver_base.py` and implement `_solve()` logic.
2. Register the solver in `core/engine/_SOLVER_TABLE` and expose a builder in `api/specs.py`.
3. Add tutorial/regression coverage (e.g., mirror the GA/SA/Hybrid tutorials with your solver).
4. Update docs: add a section to `docs/guides/scoring_deep.md` (if relevant) and `docs/guides/architecture.md`.

**Validation:** `pytest tests/solvers -q` and tutorial regressions (`pytest tests/tutorials -k <solver> -q`).

---

## Stage 4 - Add Scoring Backends or Policies
**Requirements:**
- Must keep the WLI interface stable; any new backend should match existing accuracy within tolerance.

**Steps (Expert):**
1. Implement the backend in `scoring/` (e.g., `scoring/new_backend.py`).
2. Wire it through `scoring/scoring_adapter.py` and `scoring/policy.py`.
3. Add parity tests (`tests/scoring/test_backend_selection_and_parity.py`).
4. Document configuration knobs in `docs/guides/scoring_deep.md`.

---

## FAQ
- **Can Hands-on tutorials use CLI?** Yes. IDE, CLI, and notebooks are all supported; document reproducible steps for whichever workflow you use.
- **How do I know if my change is "promotion-ready"?** Check the requirements above, ensure tests exist, and reference `docs/DOCS_PLAN.md` for tone/coverage expectations.
- **Where should I describe my new component?** Update the relevant guide (architecture, scoring, outputs) and add a recipe or tutorial entry as soon as it's promoted.

---

## Related Docs
- `docs/guides/architecture.md` - pipeline overview for promoted components.
- `docs/guides/scoring_deep.md` - backend requirements.
- `docs/howto/add_cipher.md`, `docs/howto/add_solver.md` - step-by-step recipes aligned with this ladder.

