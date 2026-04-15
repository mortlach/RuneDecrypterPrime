# V1 Core Audit Log (Bugs, Bloat, Documentation)

Date: 2026-02-23
Scope: `src/rune_decrypter_prime/core/**`
Goal: track concrete V1 issues before outward audit.

## Severity Legend
- P0: correctness or run-breaking risk
- P1: reliability/privacy/diagnostics risk
- P2: maintainability or bloat
- P3: documentation/polish

## Priority Findings

### CORE-P0-001 - Runtime validation uses `assert` in production path
- File: `src/rune_decrypter_prime/core/engine/builders.py:35`
- Evidence: `assert dev_name == Device.CUDA.value`
- Risk: `assert` is removable with optimization flags (`-O`), so requested CUDA backend validation can disappear.
- Fix direction: replace `assert` with explicit `if ...: raise RuntimeError(...)`.

### CORE-P1-001 - `_decrypt_batch` single-key fallback has ambiguous return shape contract
- File: `src/rune_decrypter_prime/core/problem/runtime.py:214`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:216`
- Evidence: when decrypt output is not 2D, code returns `list(plains)`.
- Risk: for 1D decrypt output this can become list-of-token-ints instead of list-of-plaintext arrays, which can break downstream assumptions.
- Fix direction: normalize to explicit `[np.ndarray shape (N,)]` for single-key output.

### CORE-P1-002 - Broad exception swallowing in critical score/decrypt paths
- File: `src/rune_decrypter_prime/core/problem/runtime.py:501`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:545`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:556`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:619`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:625`
- Evidence: multiple `except Exception: pass` fallbacks in batch score/raw/contiguity logic.
- Risk: can silently hide scorer/cipher contract regressions and make failures look like slow-path behavior instead of hard errors.
- Fix direction: narrow exceptions and add guarded telemetry when fallback is taken.

### CORE-P1-003 - Git dirty detection likely misses staged-only changes
- File: `src/rune_decrypter_prime/core/config/logging_config.py:176`
- Evidence: dirty check uses `git diff --quiet` only.
- Risk: staged-but-not-working-tree changes may not be represented in run metadata.
- Fix direction: combine `git diff --quiet` and `git diff --cached --quiet`.

### CORE-P1-004 - Identity fields default to non-redacted in META
- File: `src/rune_decrypter_prime/core/config/logging_config.py:50`
- File: `src/rune_decrypter_prime/core/config/logging_config.py:202`
- File: `src/rune_decrypter_prime/core/config/logging_config.py:203`
- Evidence: `redact_identity` defaults to `False`, writes `user` and `host` by default.
- Risk: benchmark bundle sharing can leak contributor machine identity.
- Fix direction: flip default to redacted or force redaction in benchmark runner configs.

### CORE-P2-001 - `DecryptionProblem` monolith with duplicated degeneracy paths
- File: `src/rune_decrypter_prime/core/problem/runtime.py:751`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:882`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:538`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:496`
- Evidence: near-duplicate code in raw vs non-raw paths and degeneracy resolvers.
- Risk: behavior drift and bug-fix duplication.
- Fix direction: refactor shared decrypt->candidate->score loops into one path with pluggable score adapter.

### CORE-P2-002 - Large dead commented block in compatibility shim
- File: `src/rune_decrypter_prime/core/config.py:40`
- File: `src/rune_decrypter_prime/core/config.py:368`
- Evidence: hundreds of commented-out legacy class/function code lines remain in module body.
- Risk: noise, review friction, mistaken edits in dead code.
- Fix direction: remove commented block; keep history in git.

### CORE-P2-003 - `types.py` mixes concerns and duplicates imports
- File: `src/rune_decrypter_prime/core/types.py:217`
- File: `src/rune_decrypter_prime/core/types.py:218`
- File: `src/rune_decrypter_prime/core/types.py:219`
- Evidence: second import block and late enum/dataclass declarations in same file.
- Risk: readability and ownership confusion.
- Fix direction: split into `types_base.py` and `types_scoring.py` (or equivalent), remove duplicate imports.

### CORE-P2-004 - Minor code hygiene in config modules
- File: `src/rune_decrypter_prime/core/config/cipher.py:5`
- File: `src/rune_decrypter_prime/core/config/cipher.py:44`
- File: `src/rune_decrypter_prime/core/solver_engine.py:12`
- Evidence: duplicate `from __future__ import annotations`, stray comment `# meh`, unused imports in solver shim.
- Risk: low, but contributes to maintenance drag.
- Fix direction: remove duplicates/unused imports and non-professional comments.

### CORE-P3-001 - Docstring/comment encoding artifacts and stale wording
- File: `src/rune_decrypter_prime/core/config/solution.py:26`
- File: `src/rune_decrypter_prime/core/problem/instance.py:53`
- File: `src/rune_decrypter_prime/core/README.txt:4`
- File: `src/rune_decrypter_prime/core/config/logging_config.py:35`
- Evidence: mojibake characters (`â...`) and one stale default path mention (`out` vs actual `output`).
- Risk: confusion for contributors and lowers external polish.
- Fix direction: normalize encoding to UTF-8 text and update docs to match behavior.

## Core File Ledger (Initial Pass)

- `src/rune_decrypter_prime/core/problem/runtime.py`: P0/P1/P2 issues open (contracts, broad excepts, duplication).
- `src/rune_decrypter_prime/core/engine/builders.py`: P0 issue open (`assert` runtime check).
- `src/rune_decrypter_prime/core/config/logging_config.py`: P1/P3 issues open (privacy default, git dirty coverage, stale doc line).
- `src/rune_decrypter_prime/core/config.py`: P2 issue open (large commented dead block).
- `src/rune_decrypter_prime/core/types.py`: P2 issue open (mixed concerns, duplicate import block).
- `src/rune_decrypter_prime/core/config/cipher.py`: P2 issue open (duplicate future import, stray comment).
- `src/rune_decrypter_prime/core/solver_engine.py`: P2 issue open (unused imports; compatibility layer clutter).
- `src/rune_decrypter_prime/core/config/scoring.py`: no clear correctness bug found in this pass; keep under watch for strict objective validation coupling.
- `src/rune_decrypter_prime/core/engine/engine.py`: no high-severity bug found; several defensive broad except blocks reduce diagnostics.
- `src/rune_decrypter_prime/core/problem/instance.py`: low-risk broad exception around ciphertext length inference.
- `src/rune_decrypter_prime/core/config/hard_crib.py`: generally clean; defensive exception use acceptable.
- `src/rune_decrypter_prime/core/config/interruptor.py`: generally clean.
- `src/rune_decrypter_prime/core/config/run.py`: generally clean; header comments reference wrong module path label.
- `src/rune_decrypter_prime/core/config/solution.py`: mostly clean; encoding artifacts in docstring.
- `src/rune_decrypter_prime/core/config/solver.py`: generally clean.
- `src/rune_decrypter_prime/core/telemetry.py`: generally clean.
- `src/rune_decrypter_prime/core/transpositions.py`: generally clean.
- `src/rune_decrypter_prime/core/factory.py`: clean compatibility shim.
- `src/rune_decrypter_prime/core/logging_config.py`: clean re-export shim.
- `src/rune_decrypter_prime/core/config/__init__.py`: clean export surface.
- `src/rune_decrypter_prime/core/problem/spec.py`: clean thin spec object.
- `src/rune_decrypter_prime/core/problem/__init__.py`: clean export surface.
- `src/rune_decrypter_prime/core/engine/__init__.py`: clean lazy-export shim.
- `src/rune_decrypter_prime/core/__init__.py`: no content; acceptable.
- `src/rune_decrypter_prime/core/README.txt`: documentation polish issue only (encoding artifacts).

## Suggested Fix Order (V1)
1. CORE-P0-001 (`assert` to runtime error).
2. CORE-P1-001/002 (runtime shape contract + narrow critical fallback exceptions).
3. CORE-P1-003/004 (logging metadata integrity + privacy-by-default for share workflows).
4. CORE-P2-001/002/003/004 (de-dup and cleanup pass).
5. CORE-P3-001 (docs/polish cleanup).

## Outward Audit Next (after core)
- `src/rune_decrypter_prime/scoring/**`: parity/contract checks (AVG vs PCT behavior, ECDF coupling).
- `src/rune_decrypter_prime/io/**`: bundle/log privacy and path normalization checks.
- `tools/benchmarks/**`: runner consistency, shared config usage, and report schema integrity.
