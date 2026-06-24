# RunSpec Reference

Status: staged V1 draft

Owner:

```text
src/rune_decrypter_prime/api/run_spec.py
```

`RunSpec` is the typed recipe for an RDP run.

## Fields

| Field | Meaning |
| --- | --- |
| `problem_input` | `RawTextInput`, `NormalizedInput`, or `SourceInputRef`. |
| `cipher` | A `CipherSpec`. |
| `key` | A `KeySpec`, or a two-item tuple of `KeySpec` values. |
| `solver` | A `SolverSpec`. |
| `scorer` | Scorer name, defaulting to `rune`. |
| `scorer_params` | JSON-primitive scorer parameters. |
| `logging` | Optional logging config. |
| `encoding_dir` | Rune text direction. |
| `device` | Device selection. |
| `telemetry_on` | Whether telemetry is enabled. |

## Problem Inputs

| Type | Use |
| --- | --- |
| `RawTextInput` | Direct text input. |
| `NormalizedInput` | Already-normalized rune indices, with optional WLI. |
| `SourceInputRef` | A typed reference to a known source such as a Liber Primus label, locator, or partition. |

## SourceInputRef LP Kinds

| Source kind | Meaning |
| --- | --- |
| `liber_primus.label` | Named LP source label. |
| `liber_primus.locator` | Typed LP locator. |
| `liber_primus.partition` | Typed LP partition. |

`SourceInputRef` validates supported keys early. Recipe labels are not accepted
as source labels.

## Design Notes

`RunSpec` should describe input and configuration. It should not hide runtime
results, generated artifacts, or tutorial acceptance policy.
