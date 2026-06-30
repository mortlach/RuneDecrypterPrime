# Core Module Map

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/`
- `tutorials/v1/`
- `tests/`

Related tests:
- `tests/docs/test_v1_coder_docs_contract.py`

Stability:
- Semi-stable contributor surface

## Purpose

This page maps the main source areas. It is intentionally conservative: an
inventory row explains where code lives and what it appears to own, but it does
not make every object in that package public API.

Use `reference/public_api_allowlist.md` for the current public support
allowlist. Use the later pipeline pages for deeper behaviour contracts.

## Package Inventory

| Source path | Purpose | Main public objects | Related tests | Documentation status | Stability |
| --- | --- | --- | --- | --- | --- |
| `src/rune_decrypter_prime/api/` | Front-door run/spec/report surfaces, display summaries, wrappers, source resolution, and user-facing builders. | `RunSpec`, `RunResult`, `CipherSpec`, `KeySpec`, `SolverSpec`, `SolverReport`, `RunAPI`, `run` | `tests/api/`, `tests/api_contract/`, `tests/contracts/` | Inventory drafted; public boundary started. | Public V1 surface plus internal helpers. |
| `src/rune_decrypter_prime/core/` | Strict core types, config, engine wiring, capability gates, component contracts, and problem/runtime boundaries. | `Direction`, `Device`, `LoggingConfig`, core config dataclasses, engine/problem entry points | `tests/core/`, `tests/core_config/`, `tests/core_types/`, `tests/guardrails/`, `tests/pipeline/` | Inventory drafted; field-level docs pending. | Mixed public, contributor, and internal surfaces. |
| `src/rune_decrypter_prime/ciphers/` | Concrete cipher implementations, cipher registry, shared keyed-cipher base, and pipeline mixin. | Registered cipher classes such as Vigenere, substitution, columnar, railfence, autokey, scheduled stream lookup | `tests/ciphers/` | Inventory drafted; cipher pipeline page pending. | Semi-stable contributor surface plus internals. |
| `src/rune_decrypter_prime/keyops/` | Key generation, mutation, validation, batching, capability description, and keyops registry. | `KeyOpBase`, `KeyCaps`, `VectorKeyOps`, `PermutationKeyOps`, `CompositeKeyOps`, registry helpers | `tests/keyops/` | Inventory drafted; key pipeline page pending. | Semi-stable contributor surface plus internals. |
| `src/rune_decrypter_prime/solvers/` | Search algorithms over key space and progress reporting helpers. | `beam`, `ga`, `sa`, `hybrid`, `kaeding_periodic_structured`, `SolverBase` | `tests/solvers/`, `tests/telemetry/`, `tests/smoke/` | Inventory drafted; solver pipeline page pending. | Semi-stable contributor surface plus internals. |
| `src/rune_decrypter_prime/scoring/` | Scoring objective implementation, scorer reports, language-model runtime, optional hamming/span/ngram components, and backend adapters. | `ScorerReport`, scorer report builders, rune scorer modules, scorer lane reports | `tests/scoring/`, `tests/torch/`, `tests/core/` | Inventory drafted; scoring pipeline page pending. | Public reports plus internal runtime. |
| `src/rune_decrypter_prime/backends/` | Optional array backend selection and device/probe helpers for NumPy/Torch/CuPy-style runtimes. | Backend selection helpers in `xp.py` | `tests/core/`, `tests/scoring/`, `tests/torch/` | Inventory drafted; backend policy docs pending. | Internal/contributor surface. |
| `src/rune_decrypter_prime/io/` | Logging adapters, run logger, artifact path policy, telemetry glue, and deterministic RNG helpers. | `RNGController`, `RunLogger`, artifact path helpers | `tests/test_logging_paths.py`, `tests/test_run_logger_paths.py`, `tests/test_artifact_policy.py`, `tests/rng_controller/` | Inventory drafted; reports/artifacts page pending. | Internal/contributor surface. |
| `src/rune_decrypter_prime/telemetry/` | Telemetry event helpers, pipeline metadata blocks, schema helpers, and mutable telemetry bag. | `make_pipeline_block`, solver/run event helpers, `TelemetryBag` | `tests/telemetry/` | Inventory drafted; telemetry/report page pending. | Internal/contributor surface. |
| `src/rune_decrypter_prime/data/` | Built-in data adapters, asset paths, Liber Primus source resolution, small cipher fixtures, and wordlist loaders. | Liber Primus typed helpers and wordlist loaders where explicitly documented | `tests/data/`, `tests/api/`, `tests/assets/` | Inventory drafted; data/reference docs pending. | Mixed public data helpers and internals. |
| `src/rune_decrypter_prime/utils/` | Tutorial, reporting, pretty output, runeglish, transposition, seed, and compatibility utilities. | Tutorial runner/report helpers are semi-stable; most helpers are internal unless documented. | `tests/utils/`, `tests/tutorials/`, `tests/contracts/` | Inventory drafted; tutorial utility boundary pending. | Semi-stable for tutorials; otherwise mixed. |
| `src/rdp/` | Lightweight alias package for friendlier imports in tutorials and sample code. | `api` alias and mirrored root package exports | `tests/installation/`, import-surface tests where present | Inventory drafted; public alias policy pending. | Public convenience alias with minimal logic. |
| `tutorials/v1/` | Promoted V1 tutorial scripts, runner, and tutorial manifest. | Tutorial runner entry point and manifest data. | `tests/tutorials/`, `tests/contracts/`, `tests/utils/` | Existing V1 docs started. | Public tutorial surface. |
| `tests/` | Contract, regression, smoke, tutorial, docs, and unit tests. | Test helpers only where explicitly documented. | `tests/` | Existing test docs started. | Test-only helper surface. |

## Package Notes

### `src/rune_decrypter_prime/api/`

Owns the user-facing request and result language. This includes specs,
wrappers, normalisation, source resolution, run orchestration, display summaries,
solver reports, and artifact manifests.

Important files:

- `src/rune_decrypter_prime/api/__init__.py`
- `src/rune_decrypter_prime/api/run.py`
- `src/rune_decrypter_prime/api/run_spec.py`
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/api/run_result.py`
- `src/rune_decrypter_prime/api/solver_report.py`
- `src/rune_decrypter_prime/api/run_artifact_manifest.py`
- `src/rune_decrypter_prime/api/display.py`
- `src/rune_decrypter_prime/api/printer.py`
- `src/rune_decrypter_prime/api/wrappers/`

Boundary note: `api/__init__.py` re-exports a friendly surface, but the current
public support allowlist is intentionally narrower.

### `src/rune_decrypter_prime/core/`

Owns strict internal runtime structure: enums, config dataclasses, engine
entry points, capability gates, component contracts, transposition helpers, and
problem/runtime objects.

Important paths:

- `src/rune_decrypter_prime/core/types.py`
- `src/rune_decrypter_prime/core/config/`
- `src/rune_decrypter_prime/core/engine/`
- `src/rune_decrypter_prime/core/problem/`
- `src/rune_decrypter_prime/core/component_contracts.py`
- `src/rune_decrypter_prime/core/capability_gates.py`

Boundary note: some core config and enum objects are stable enough to document,
but engine/runtime helpers need deeper WP3-WP6 inspection before becoming
public promises.

### `src/rune_decrypter_prime/ciphers/`

Owns concrete transformations between ciphertext and plaintext for a fully
formed key. It should not own key search, key mutation, ranking, or report
generation.

Important paths:

- `src/rune_decrypter_prime/ciphers/base_keyed_cipher.py`
- `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py`
- `src/rune_decrypter_prime/ciphers/registry.py`
- `src/rune_decrypter_prime/ciphers/generic_map_cipher.py`
- `src/rune_decrypter_prime/ciphers/scheduled_stream_lookup_cipher.py`
- `src/rune_decrypter_prime/ciphers/dev/`

Boundary note: `ciphers/dev/` is development/experimental unless a later stage
promotes specific items.

### `src/rune_decrypter_prime/keyops/`

Owns key operations that solvers use without knowing cipher details:
normalisation, validation, random key generation, mutation, recombination, and
batch neighbour generation.

Important paths:

- `src/rune_decrypter_prime/keyops/base_keyops.py`
- `src/rune_decrypter_prime/keyops/registry.py`
- `src/rune_decrypter_prime/keyops/vector.py`
- `src/rune_decrypter_prime/keyops/permutation_ops.py`
- `src/rune_decrypter_prime/keyops/composite.py`
- `src/rune_decrypter_prime/keyops/dev/`

Boundary note: the contributor surface is the family/registry pattern, not every
helper method in every keyops module.

### `src/rune_decrypter_prime/solvers/`

Owns search algorithms. Solvers should ask the problem to evaluate candidate
keys and should rely on keyops for candidate generation/manipulation.

Important paths:

- `src/rune_decrypter_prime/solvers/solver_base.py`
- `src/rune_decrypter_prime/solvers/beam.py`
- `src/rune_decrypter_prime/solvers/ga.py`
- `src/rune_decrypter_prime/solvers/sa.py`
- `src/rune_decrypter_prime/solvers/hybrid.py`
- `src/rune_decrypter_prime/solvers/kaeding_periodic_structured.py`
- `src/rune_decrypter_prime/solvers/progress/`

Boundary note: seed behaviour, effective seed reporting, stop reasons, and
backend assumptions belong in the later solver pipeline page.

### `src/rune_decrypter_prime/scoring/`

Owns scoring/ranking implementation and scorer report surfaces. This area is
high-risk for silent drift because some values rank candidates while other
values are diagnostics only.

Important paths:

- `src/rune_decrypter_prime/scoring/rune_scorer.py`
- `src/rune_decrypter_prime/scoring/rune_scorer_impl.py`
- `src/rune_decrypter_prime/scoring/scorer_report.py`
- `src/rune_decrypter_prime/scoring/scorer_report_builder.py`
- `src/rune_decrypter_prime/scoring/scorer_lane_report.py`
- `src/rune_decrypter_prime/scoring/language_model/`
- `src/rune_decrypter_prime/scoring/hamming/`
- `src/rune_decrypter_prime/scoring/span_hamming/`
- `src/rune_decrypter_prime/scoring/ngram_hamming/`
- `src/rune_decrypter_prime/scoring/torch_backend/`

Boundary note: scoring docs must always say whether a signal affects ranking,
stopping, tie-breaks, candidate selection, or diagnostics only.

### `src/rune_decrypter_prime/backends/`

Owns optional runtime backend detection and small array-backend adapters.

Important paths:

- `src/rune_decrypter_prime/backends/xp.py`
- `src/rune_decrypter_prime/backends/device.py`

Boundary note: this is not a general math layer. Keep backend claims tied to
the small API actually used by scoring/solver code.

### `src/rune_decrypter_prime/io/`

Owns logging, artifact path policy, telemetry I/O glue, and deterministic RNG
helpers.

Important paths:

- `src/rune_decrypter_prime/io/artifact_policy.py`
- `src/rune_decrypter_prime/io/run_logger.py`
- `src/rune_decrypter_prime/io/rng.py`
- `src/rune_decrypter_prime/io/logging_adapter.py`

Boundary note: generated run outputs belong under approved output roots, not in
docs or source folders.

### `src/rune_decrypter_prime/telemetry/`

Owns structured telemetry event creation and pipeline block metadata.

Important paths:

- `src/rune_decrypter_prime/telemetry/events.py`
- `src/rune_decrypter_prime/telemetry/pipeline.py`
- `src/rune_decrypter_prime/telemetry/schema.py`
- `src/rune_decrypter_prime/telemetry/bag.py`

Boundary note: telemetry should explain a run and preserve evidence. It should
not become hidden control flow.

### `src/rune_decrypter_prime/data/`

Owns code-side access to bundled data and small fixtures. Heavy runtime assets
remain under `assets/` and are governed by asset manifests and policy.

Important paths:

- `src/rune_decrypter_prime/data/asset_paths.py`
- `src/rune_decrypter_prime/data/liber_primus/`
- `src/rune_decrypter_prime/data/wordlists/`
- `src/rune_decrypter_prime/data/cipher_tests/`
- `src/rune_decrypter_prime/data/language_model/`

Boundary note: source data helpers must not be confused with generated run
outputs or external large-asset bundles.

### `src/rune_decrypter_prime/utils/`

Owns cross-cutting helpers, especially tutorial/report support and text utility
code.

Important paths:

- `src/rune_decrypter_prime/utils/runeglish.py`
- `src/rune_decrypter_prime/utils/tutorial_runner.py`
- `src/rune_decrypter_prime/utils/tutorial_report.py`
- `src/rune_decrypter_prime/utils/tutorial_session_report.py`
- `src/rune_decrypter_prime/utils/tutorial_output.py`
- `src/rune_decrypter_prime/utils/solve_output.py`
- `src/rune_decrypter_prime/utils/transposition.py`

Boundary note: tutorial utilities can be semi-stable because tutorials depend
on them. Other utility helpers remain internal unless promoted deliberately.

### `src/rdp/`

Owns the short import alias for friendlier tutorial/sample code.

Important paths:

- `src/rdp/__init__.py`
- `src/rdp/README.txt`

Boundary note: keep this package import-only and lightweight.

### `tutorials/v1/`

Owns promoted tutorial scripts, the V1 runner, and tutorial manifest data.

Important paths:

- `tutorials/v1/run_tutorials.py`
- `tutorials/v1/tutorial_manifest_v1.json`

Boundary note: tutorials are release evidence for their exact scenario. They
are not automatically broad production support promises.

### `tests/`

Owns contract, regression, smoke, tutorial, docs, and unit tests.

Important paths:

- `tests/contracts/`
- `tests/api/`
- `tests/core/`
- `tests/scoring/`
- `tests/tutorials/`
- `tests/docs/`

Boundary note: test helpers are test-only unless explicitly documented
elsewhere.

## Current Focus And Remaining Inventory Work

WP1 inventory is drafted for each top-level package. The next inventory
expansion should add:

- exact owner modules for config objects in `src/rune_decrypter_prime/core/config/`
- source-to-test links for each cipher family
- source-to-test links for each scorer lane/report surface
- explicit boundaries for `src/rune_decrypter_prime/ciphers/dev/` and
  `src/rune_decrypter_prime/keyops/dev/`
- a checked list of public aliases in `src/rdp/`

## What Not To Infer

This page is not a promise that every module under a listed package is public.
Use `reference/public_api_allowlist.md` for the current public allowlist.
