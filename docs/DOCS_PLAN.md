# Rune Decrypter Prime - v1 Design Document (Public Release)

> This document defines the **canonical structure, naming, and authoring rules** for the v1 public release. It aligns the codebase, tests, tutorials, and docs so that **beginner solvers** can run and learn, while **experts** can extend and validate.

---

## 0. Goals & Non-Goals

### Goals

* **Deterministic** by default (fixed seeds, eval budgets, reproducible outputs).
* **Transparent**: enums on the surface, telemetry everywhere, human-readable outputs.
* **Teach then deepen**: simple runnable tutorials first, expert deep dives later.
* **Single path through the system** (no duplicate "pipelines" from the user point of view).
* **Device parity** (CPU↔CUDA) guarded by tests.
* **Infinitely extensible** with user plug-in ciphers, keyops, pipeline extensions, etc.
* **Docs↔Code sync**: automated symbol & path checks ensure docs stay valid as code moves.

### Non-Goals

* We do **not** provide a command-line interface in v1.
* We do **not** promise stability for code in `dev/` folders (they are visible, not supported).

---

## 1. Audiences & Tone

* **Hands-on track (beginner)**: short explanations, immediately runnable scripts, plain language, "you can" phrasing.
* **Expert track**: "Under the hood" sections link to modules and tests, with explicit contracts and telemetry keys.

All docs use **Plain English**, no hype, no "just".

---

## 2. Support Boundary (v1)

**Supported surface (v1):**

* `src/rune_decrypter_prime/api/*`
* `src/rune_decrypter_prime/core/*` (except `core/legacy/*`)
* `src/rune_decrypter_prime/solvers/*`
* `src/rune_decrypter_prime/scoring/*`
* `src/rune_decrypter_prime/telemetry/*`
* `src/rune_decrypter_prime/keyops/*`
* `src/rune_decrypter_prime/ciphers/*` (production ciphers only)

**Visible but not supported (experimental):**

* `src/rune_decrypter_prime/ciphers/dev/`
* `src/rune_decrypter_prime/keyops/dev/`
* `tutorials/v1/dev/`

> These are included so learners can see the frontier. APIs may change; determinism is not guaranteed; they're not re-exported by package `__init__.py`.

---

## 3. Canonical Repository Layout

```
/ (repo root)
├─ README.md
├─ CONTRIBUTING.md
├─ LICENSE
├─ pyproject.toml
├─ .github/workflows/ci.yml
├─ src/
│  ├─ rdp/
│  │  └─ __init__.py
│  └─ rune_decrypter_prime/
│     ├─ api/
│     ├─ backends/
│     ├─ ciphers/
│     │  ├─ dev/
│     ├─ core/
│     │  ├─ engine/
│     │  ├─ problem/
│     │  └─ legacy/
│     ├─ data/
│     ├─ io/
│     ├─ keyops/
│     │  └─ dev/
│     ├─ solvers/
│     ├─ scoring/
│     ├─ telemetry/
│     ├─ utils/
│     └─ __init__.py
├─ tutorials/
│  └─ v1/
│     ├─ Start_Here.py
│     ├─ Vigenere_GeneralMap.py
│     ├─ ColumnarTransposition.py
│     ├─ MonoSubstitution_SA.py
│     ├─ MonoSubstitution_GA.py
│     ├─ MonoSubstitution_HYBRID.py
│     ├─ CribDrag_Example.py
│     └─ dev/
├─ docs/
│  ├─ guides/
│  ├─ howto/
│  ├─ reference/
│  ├─ tutorials/
│  ├─ appendices/
│  ├─ tests_docs/
│  └─ repo/
├─ tests/
└─ tools/
   ├─ docs_lint/
   ├─ scaffold/
   ├─ symbols/
   ├─ benchmarks/
   └─ repo_utils/
```

### Decisions (applied now)

* **Tutorials live outside `src/`** to keep the package clean and the learner path obvious.
* `core/solver_engine.py` moves to **`core/legacy/solver_engine.py`** (kept for reference/tests).
* `ciphers/pipeline.py` is renamed to **`ciphers/cipher_pipeline.py`** to avoid clashing with API "pipeline".
* Keep the **alias** `src/rdp/__init__.py` so docs can say `import rdp` for newcomers.
* Dev folders **ship** but are fenced with README banners and excluded from public `__all__`.

---

## 4. Single Path Through the System

```
User code ─▶ api/run.py ─▶ api/normalize.py ─▶ core/problem/spec.py
         │                                 │
         │                                 └▶ core/problem/instance.py -> runtime.py
         └───────────────────────────────────────────────▶ core/engine/engine.py
                                                           │
                                                           ├▶ solvers/{sa,ga,beam,hybrid}.py
                                                           └▶ scoring/* (NumPy/Torch backends)
Telemetry/logs ◀────────────────────────────────────────── io/run_logger.py + telemetry/*
```

**Guarantee:** the public docs and examples only show the **API->Problem->Engine->Solver->Scoring** path above.

---

## 5. Naming & Conventions

* **Enums only** on the public surface; no magic strings.
* Filenames are **ASCII** (tutorials, especially).
* Public "pipeline" = **`api/run.py`** (entry), **`api/pipeline.py`** (orchestrator).
  Internal cipher mechanics = **`ciphers/cipher_pipeline.py`**.
* All public examples set an explicit **`seed`** and prefer **evaluation budgets** over time limits.

---

## 6. Determinism Contract (one-pager for users)

* Always pass a fixed **`seed`** into solvers (and record it).
* Prefer fixed **iterations/evaluations** over time budgets.
* Device parity: CPU and CUDA results must agree within tolerances;
  guarded by `tests/smoke/test_cuda_solver.py` and `tests/smoke/test_runapi_determinism.py`.
* **Report package versions** and attach `output/.../META.json` when sharing results.

---

## 7. Output & Telemetry

**Output tree**: `output/<kind>/<timestamp>__<label>__<git>/`

* `META.json` - seed, device, solver, pipeline summary, git short hash
* `logs/` - structured JSONL events
* `trace/` - solver spans
* `artifacts/` - per-run exports (e.g., best candidates)

**Telemetry minimum (v1):**

* run metadata (seed, device, cipher, scorer)
* solver spans (optimizer params, rounds, candidate counts, timings)
* pipeline block (direction, length, permutation hash)
* scoring snapshot (objective, backend)

---

## 8. Tutorials (Hands-on track)

**Start Here**: `tutorials/v1/Start_Here.py` - a 20-line Vigenère run that prints plaintext, key, and where to find `META.json`.
Every other tutorial is a single idea and <80 lines.
Advanced/variants go in `tutorials/v1/dev/` with ASCII names.

> All tutorials run from PyCharm by pressing **Run**. No CLI anywhere.

---

## 9. Docs Set (authoring rules)

Every guide uses this template:

* **What it is**
* **Why it matters** (determinism / telemetry / outputs)
* **How to use it**

  * Hands-on (IDE steps)
  * Expert (code entry points; tests that validate the behaviour)
* **Code references** (relative paths)
* **Examples / Tutorials**
* **How-to / FAQ** (2-3 items)
* **Benchmarks / Validation** (tests that assert ranges/contracts)
* **Related docs**

**Key guides (initial):**

* `docs/guides/getting_started.md`, `architecture.md`, `philosophy.md`, `outputs.md`, `learning_ladder.md`, `determinism_contract.md`

**How-to recipes:**

* `docs/howto/add_a_cipher.md`, `add_a_solver_move.md`, `read_telemetry.md`, `reproduce_a_run.md`

**Reference (supported surface):**

* Mirrors package directories; each page leads with **"What it represents"** and lists tests that assert behaviour.
* Dev pages exist but **labelled experimental**.

**Appendices:**

* `high_school_troubleshooting.md`, `faq.md`, `glossary.md`

### 9A. Docs↔Code Sync (tools-backed, IDE-run)

**Purpose.** Keep docs in lock-step with code by automatically checking:

* Paths and filenames mentioned in docs actually exist.
* Referenced classes/functions/methods actually exist (and where).
* Code blocks are syntactically sane.

**Two building blocks:**

1. **Project Symbol Indexer** - scans `src/` for top-level classes, functions, and class methods, and writes a flat index to `output/share/<timestamp>__share__symbols/project_symbol_index.txt`. Excludes common cache/virtual-env folders, parses with `ast`, and normalises relative file paths.  

2. **Docs Linter** - walks `docs/`, parses fenced code blocks for syntax sanity, checks links/paths, and emits a JSON + Markdown report with counts such as `pages_scanned`, `syntax_error_blocks`, and coverage summaries (functions/classes documented vs total).  

**Authoring conventions (enforced by the linter):**

* When you name a specific symbol in prose, use **code refs** in the form
  `path/to/file.py::SymbolName` or `path/to/file.py::ClassName.method`.
  These are resolved against the **Project Symbol Index**.
* Prefer **relative paths under `src/`** and keep them stable in headings or "Code references" sections.
* Keep code fences valid; avoid ellipses `...` inside Python blocks unless they're literal strings (these have been a common source of syntax flags). 

**Quality gates (docs):**

* `syntax_error_blocks == 0`
* `broken_links == 0`
* `pages_scanned > 0`
* Symbol resolution succeeds for all `::` code refs (no unresolved entries).
* Coverage trend must not regress materially (documented/total classes & functions) relative to last release snapshot. The linter reports these counts to help track drift. 

---

## 10. Tests & Validation Strategy

* **Guardrails** (`tests/guardrails/*`): no magic literals; only enums; no legacy defaults; UI not imported.
* **Determinism & parity** (`tests/smoke/*`): run-API determinism; CUDA presence and parity.
* **Pipeline contracts** (`tests/pipeline/*`): spec->instance; permutation tracking.
* **Solvers** (`tests/solvers/*`): permutation optimisers.
* **Scoring** (`tests/scoring/*`): backend selection and parity; Windows stats/telemetry checks.
* **Telemetry** (`tests/telemetry/*`): schema, minimum keys, solver progress, pipeline block.
* **Ciphers** (`tests/ciphers/*`): device parity, degeneracy, keylength, custom map definition.
* **Tutorials** (`tests/tutorials/*`): crib-drag API; GA/SA/Hybrid regressions.
* **Types & API contracts** (`tests/api*`, `tests/core_types/*`).

> Docs state explicitly which tests validate each claim.

---

## 11. Tools & Scaffolding

* **docs_lint** (`tools/docs_lint/docs_lint.py`)
  Runs path/symbol checks against the **Project Symbol Index**, verifies headings/anchors, validates fenced code syntax, and writes JSON + Markdown reports under `tools/docs_lint/reports/`. Tracks `pages_scanned`, `syntax_error_blocks`, coverage and more.  

* **symbols: Project Symbol Indexer** (`tools/symbols/index_project_symbols.py`)
  IDE-run utility that scans `src/`, excludes caches/venvs, builds a list of `file / name / signature / docstring_head`, and writes to `output/share/<timestamp>__share__symbols/project_symbol_index.txt`. This is the **sole ground truth** for symbol existence/location used by docs checks.  

* **scaffold** (`tools/scaffold/new_cipher_scaffold.py`): create a minimal cipher module with docstrings and a test stub.

* **benchmarks** (`tools/benchmarks/benchmark_harness.py`): IDE-run harness with fixed seeds and evaluation budgets (no time budgets).

* **repo_utils/**: shared utilities (e.g., tidy layout, share package zip).

> All tools are **PyCharm-run**. No CLI steps are documented.

### 11A. Docs Sync Workflow (pre-commit, release, CI)

**For authors (PyCharm):**

1. Run **Project Symbol Indexer** -> confirm a fresh `project_symbol_index.txt` is produced under `output/share/...`. 
2. Run **Docs Linter** -> inspect the Markdown report; fix any path/symbol/syntax issues. 

**CI (minimal):**

* Step 1: run Symbol Indexer (writes to an artefact path).
* Step 2: run Docs Linter; **fail** if quality gates in §9A are violated.

---

## 12. Contribution & Release

* **Contribution rules** (CONTRIBUTING.md):

  * British English; IDE-first; enums on surface; small PRs.
  * Include tests as ground truth; fix seeds.
  * For new examples, add one tutorial and one validation test.
  * **Docs sync required**: update code refs and re-run the two tools; attach the linter report to the PR.

* **Release**:

  * `pyproject.toml` for packaging metadata.
  * Minimal CI at `.github/workflows/ci.yml` runs **symbol index** then **docs_lint** and a small test slice.
  * A source release zip can be generated with `tools/repo_utils/share_package.py` (IDE-run).

---

## 13. Migration Notes (from current tree)

Apply these **once** and update imports where noted:

1. Move `src/rune_decrypter_prime/core/solver_engine.py` -> `src/rune_decrypter_prime/core/legacy/solver_engine.py`. Add module banner: "DEPRECATED (v1) - kept for tests only."
2. Rename `src/rune_decrypter_prime/ciphers/pipeline.py` -> `src/rune_decrypter_prime/ciphers/cipher_pipeline.py`. Update local imports accordingly.
3. Move **all tutorials** from `src/rune_decrypter_prime/tutorials/v1/` into top-level `tutorials/v1/` (ASCII filenames; add `Start_Here.py`).
4. Keep `ciphers/dev/` and `keyops/dev/` but add `README.md` banners explaining they're experimental.
5. Consolidate duplicate tools into `/tools`, placing general utilities under `/tools/repo_utils/`.
6. (Optional tidy) Rename `tests/patche_old_ui/` -> `tests/legacy_ui/` (update imports in those tests).

---

## 14. Roadmap (v1.x)

* Promote Rail Fence, Hill and Route from `dev/` once they pass determinism and have tutorials + tests.
* Human-friendly telemetry overlay: short summaries in outputs for non-technical readers.
* Scoring presets doc tightened by an "Objective picker" guide for hands-on readers.

---

## 15. Decision Log (high level)

* Tutorials live **outside** `src/` for clarity.
* Keep **dev** folders visible, but **not supported**.
* Short import alias **`rdp`** included for newcomers.
* Public "pipeline" is **API-level**; cipher intrinsics renamed to **`cipher_pipeline.py`**.
* Legacy solver path quarantined under **`core/legacy/`**.
* No CLI in docs; everything is **PyCharm** runnable.
* **Docs sync is mandatory** via the two tools; CI enforces it.

---

### Appendix A - Dev README (banner text)

**`src/rune_decrypter_prime/ciphers/dev/README.md`**

```
# Experimental ciphers (dev)
This folder is visible for learning and research, but **not** supported in v1.
APIs may change, determinism is not guaranteed, and modules are not re-exported by the package.
Please add a tutorial and a minimal test before proposing promotion to production.
```

**`src/rune_decrypter_prime/keyops/dev/README.md`**

```
# Experimental key operations (dev)
Visible for exploration, not part of v1 surface. Expect change and no determinism guarantees.
```

---

**Notes on the two tools (for completeness):**

* The **symbol indexer** writes to `output/share/<timestamp>__share__symbols/...` and is designed to be run from anywhere inside the repo; it discovers the repo root and excludes caches/virtualenvs before scanning `src/`. 
* The **docs linter** surfaces metrics (e.g., `pages_scanned`, `syntax_error_blocks`, documented/total classes & functions) and a Markdown report suitable for PRs. Use this to spot syntax issues like ellipses `...` inside Python fences, which commonly trigger parse errors.  




