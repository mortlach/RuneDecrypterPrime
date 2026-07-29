# Config Objects

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/api/run_spec.py`
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/core/config/logging_config.py`
- `src/rune_decrypter_prime/core/types.py`

Related tests:
- `tests/docs/test_v1_coder_docs_contract.py`
- `tests/api/`
- `tests/api_contract/`
- `tests/core_config/`
- `tests/core_types/`
- `tests/contracts/`

Stability:
- Public V1 surface for `RunSpec`, input objects, front-door specs, `Direction`, and `Device`
- Semi-stable contributor surface for `LoggingConfig`

## Purpose

This page explains the typed objects that describe an RDP run before it reaches
the runtime engine.

These objects are the boundary between friendly user inputs and strict core
runtime structures. They should be explicit, validated, and easy to report.

## Object Map

| Object | Owner path | Role |
| --- | --- | --- |
| `RawTextInput` | `src/rune_decrypter_prime/api/run_spec.py` | Non-empty raw text input. |
| `NormalizedInput` | `src/rune_decrypter_prime/api/run_spec.py` | Already-tokenised rune indices and optional WLI. |
| `SourceInputRef` | `src/rune_decrypter_prime/api/run_spec.py` | Reference to a built-in source such as Liber Primus. |
| `RunSpec` | `src/rune_decrypter_prime/api/run_spec.py` | Durable run request. |
| `CipherSpec` | `src/rune_decrypter_prime/api/specs.py` | Declarative cipher selection. |
| `KeySpec` | `src/rune_decrypter_prime/api/specs.py` | Declarative key plan. |
| `SolverSpec` | `src/rune_decrypter_prime/api/specs.py` | Declarative solver choice, params, and seed. |
| `LoggingConfig` | `src/rune_decrypter_prime/core/config/logging_config.py` | Output, report, and run-directory controls. |
| `Direction` | `src/rune_decrypter_prime/core/types.py` | Canonical text encoding direction. |
| `Device` | `src/rune_decrypter_prime/core/types.py` | Canonical requested execution device. |

## Input Objects

### RawTextInput

Stability: Public V1 surface

| Field | Meaning | Validation/default |
| --- | --- | --- |
| `text` | Raw input text to normalise into rune-token indices. | Must be a non-empty string and not a `Path`. |

Use when the caller wants RDP to normalise text and infer WLI where possible.

### NormalizedInput

Stability: Public V1 surface

| Field | Meaning | Validation/default |
| --- | --- | --- |
| `ct_idx` | Ordered rune-token indices. | Required non-empty ordered sequence; each item must be an integer in `[0..28]`. |
| `wli` | Optional word-location information as `[pos_in_word, word_len]` pairs. | `None` by default; when supplied it must match `ct_idx` length and each pair must be valid. |

Use when the caller already has canonical rune-token indices.

### SourceInputRef

Stability: Public V1 surface

| Field | Meaning | Validation/default |
| --- | --- | --- |
| `source_kind` | Source resolver kind. | Required non-empty string. Supported Liber Primus kinds are `liber_primus.label`, `liber_primus.locator`, and `liber_primus.partition`. |
| `asset_id` | Source asset identifier. | Required non-empty string. |
| `asset_version` | Source asset version. | Required non-empty string. |
| `ref` | JSON-primitive reference payload for the selected source kind. | Defaults to `{}`; keys must be strings and values must be JSON primitives. Source-specific keys are validated. |

Use when a run should point to a built-in source without embedding raw text in
the run request.

## RunSpec

Stability: Public V1 surface

`RunSpec` is the durable description of what RDP was asked to run.

| Field | Meaning | Validation/default |
| --- | --- | --- |
| `problem_input` | Raw text, normalised token data, or built-in source reference. | Must be `RawTextInput`, `NormalizedInput`, or `SourceInputRef`. |
| `cipher` | Declarative cipher specification. | Must be `CipherSpec`. |
| `key` | Declarative key specification. | Must be `KeySpec` or a two-item tuple of `KeySpec` values. |
| `solver` | Declarative solver specification. | Must be `SolverSpec`. |
| `scorer` | Scorer family name. | Defaults to `"rune"`; must be a non-empty string. |
| `scorer_params` | Scorer parameter mapping. | Defaults to `{}`; keys must be strings and values must be finite JSON primitives. |
| `logging` | Optional output/report logging configuration. | Defaults to `None`; when supplied must be `LoggingConfig`. |
| `encoding_dir` | Text encoding direction for plaintext interpretation. | Defaults to `Direction.RTL`; must be a `Direction`. |
| `device` | Requested execution device. | Defaults to `Device.CPU`; must be a `Device`. |
| `telemetry_on` | Whether runtime telemetry is enabled. | Defaults to `True`; must be a bool. |

Important boundary: when `RunAPI.run(spec=...)` is used, durable inputs come
from the spec. The runtime rejects mixed outside durable inputs.

## CipherSpec

Stability: Public V1 surface

`CipherSpec` describes the cipher transform or wrapper choice. Runtime config
builders translate it into core `CipherConfig`.

| Field | Meaning | Validation/default |
| --- | --- | --- |
| `name` | Human/friendly cipher name. | Required by constructor/factory. |
| `N` | Alphabet size. | Defaults to `29`. |
| `kind` | Spec kind, such as `wrapper`, `user_map2`, `user_map3`, or `lookup`. | Defaults to `"UNKNOWN"`; factories set known values. |
| `function` | Callable for user-defined map specs. | Defaults to `None`; `user_map2` and `user_map3` require a callable. |
| `table` | Lookup table for table-defined specs. | Defaults to `None`. |
| `degeneracy` | Candidate degeneracy policy. | Defaults to `"forbid"`; `from_lookup` defaults to `"allow"`. |
| `resolver` | Degenerate candidate resolver. | Defaults to `"expand_beam"`. |
| `per_pos_limit` | Per-position candidate cap for degenerate mappings. | Defaults to `29`. |
| `resolver_limit` | Full plaintext candidate cap per key. | Defaults to `8193`. |
| `wrapper_core` | Core cipher name used by wrapper specs. | Defaults to `None`; wrapper factories set it. |
| `device` | Optional device hint. | Defaults to `Device.CPU`. |
| `extra` | Extra wrapper/config metadata. | Defaults to `{}`. |

Common factories include `periodic_substitution`, `periodic_columnar`,
`user_map2`, `user_map3`, and `from_lookup`.

## KeySpec

Stability: Public V1 surface

`KeySpec` is the front-door key plan. It is intentionally separate from keyops
runtime classes.

| Field | Meaning | Validation/default |
| --- | --- | --- |
| `plan` | Key plan name, such as `repeat`, `otp`, `const`, `perm`, or `periodic_structured`. | Required by constructor/factory. |
| `params` | Plan-specific parameters. | Defaults to `{}`. |
| `_align_offset` | Optional alignment/search metadata. | Defaults to `None`; set by `align(...)`. |

Common factories include `repeat`, `repeat_range`, `otp`, `const`,
`permutation`, `periodic_structured`, `periodic_substitution`,
`periodic_columnar`, `matrix2x2`, `matrix`, `affine`, and `scalar`.

Boundary note: `_align_offset` is a stored field, but the leading underscore
marks it as internal metadata. Prefer the `align(...)` method rather than
setting it directly.

## SolverSpec

Stability: Public V1 surface

`SolverSpec` records solver family, normalised parameters, and requested seed.

| Field | Meaning | Validation/default |
| --- | --- | --- |
| `name` | Solver family name. | Required by constructor/factory. Known V1 families include `beam`, `ga`, `sa`, `hybrid`, `kaeding`, and the specialised `two_period_cribs`. |
| `params` | Solver parameter mapping. | Defaults to `{}`; factories canonicalise friendly aliases where supported. |
| `seed` | Requested solver seed. | Defaults to `None`; the engine uses deterministic effective seed `0` when omitted. |

Prefer factories such as `SolverSpec.beam(...)`, `SolverSpec.ga(...)`,
`SolverSpec.sa(...)`, `SolverSpec.hybrid(...)`, and `SolverSpec.kaeding(...)`
for friendly alias handling.

`SolverSpec.two_period_cribs(...)` accepts complete fixed crib placements,
candidate words, optional explicit candidate positions, a positive start count,
and a deterministic seed. Unsupported general solver or scorer options are
rejected by the dedicated `api.run` route.

## LoggingConfig

Stability: Semi-stable contributor surface

`LoggingConfig` controls output initialisation and optional report/artifact
writing. It should be explicit; no CLI flags or environment variables are read
inside this object.

| Field | Meaning | Validation/default |
| --- | --- | --- |
| `verbose` | Enable verbose logging behaviour. | Defaults to `True`. |
| `print_progress` | Allow progress printing. | Defaults to `True`. |
| `write_jsonl` | Write JSONL event stream under logs. | Defaults to `True`. |
| `repo_root` | Explicit repository root. | Defaults to `None`; detected if omitted. |
| `out_root` | Base output directory. | Defaults to `None`; runtime defaults under repo `output/`. |
| `run_kind` | Short run category used in output path construction. | Defaults to `"run"`. |
| `label` | Optional human-friendly run label. | Defaults to `None`. |
| `fixed_run_dir` | Optional exact run directory. | Defaults to `None`; relative values are resolved under the run-kind output root. |
| `redact_identity` | Redact host/user identity in run metadata. | Defaults to `False`. |
| `portable_output` | Force portable/redacted output behaviour. | Defaults to `False`. |
| `write_solver_report` | Write `artifacts/solver_report.json`. | Defaults to `False`; must be a bool. |
| `write_rdp_display_summary` | Write `artifacts/rdp_display_summary.json`. | Defaults to `False`; must be a bool. |
| `write_run_artifacts_manifest` | Write `artifacts/run_artifacts_manifest.json`. | Defaults to `False`; must be a bool. |

Output paths must stay under the intended output root or run directory. Docs,
logs, and generated artifacts should not be written inside source docs.

## Direction

Stability: Public V1 surface

| Value | Meaning |
| --- | --- |
| `Direction.LTR` / `"ltr"` | Left-to-right text encoding direction. |
| `Direction.RTL` / `"rtl"` | Right-to-left text encoding direction. |

Reports should include `encoding_dir` whenever plaintext is interpreted.

## Device

Stability: Public V1 surface

| Value | Meaning |
| --- | --- |
| `Device.CPU` / `"cpu"` | CPU execution request. |
| `Device.CUDA` / `"cuda"` | CUDA execution request. |

Device is a request. Runtime/backend availability still has to be reported
honestly by the layers that execute scoring or solving.

## Contracts And Invariants

- Dataclass/config fields must be documented when the object is public.
- Public run objects should reject ambiguous types early.
- `RunSpec` should be path-free and reportable.
- `scorer_params` and source refs must remain JSON-primitive mappings.
- Truth/oracle data must not be smuggled through config fields without report
  visibility.
- Logging/report toggles must not silently create files outside approved output
  roots.

## Extension Notes

When adding a field to a public config object:

1. Add validation or a safe default.
2. Update this page.
3. Update focused docs-contract tests.
4. Update report/display docs if the field should be visible to users.
5. Add or update runtime tests for behavioural changes.

## What Not To Rely On

- Private helper functions in `run_spec.py`.
- Internal fields with leading underscores.
- Exact output directory names beyond the documented artifact paths.
- Raw strings where strict enums are required by `RunSpec`.
