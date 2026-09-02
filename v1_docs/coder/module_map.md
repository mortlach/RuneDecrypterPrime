# Core Module Map

Status: implemented V1 boundary

This map distinguishes the definition-owning public package from the engine
packages. Importability does not make an engine module public.

| Source path | Responsibility | Audience |
| --- | --- | --- |
| `src/rdp/api/` | Canonical V1 requests, results, operations, display, data, advanced, and experimental namespaces. | Public |
| `src/rdp/backends/` | Optional compute-backend selection. | Internal/contributor |
| `src/rdp/core/` | Canonical component contracts, runtime configuration, and problem materialisation. | Internal/contributor |
| `src/rune_decrypter_prime/ciphers/` | Runtime cipher implementations and exact materializers. | Internal/contributor |
| `src/rune_decrypter_prime/core/` | Runtime engine orchestration retained until its later AN4 move. | Internal |
| `src/rdp/data/` | Liber Primus runtime data, rune translation, and asset resolution. | Internal except promoted data API |
| `src/rune_decrypter_prime/data/` | Retained fixtures, corpora, and wordlists awaiting their later AN4 move. | Internal/test support |
| `src/rdp/io/` | Logging, artifact paths, and deterministic I/O support. | Internal |
| `src/rune_decrypter_prime/keyops/` | Key generation, validation, mutation, and batching. | Internal/contributor |
| `src/rune_decrypter_prime/scoring/` | Candidate ranking and scorer reports. | Internal except promoted report types |
| `src/rune_decrypter_prime/solvers/` | Search algorithms over key spaces. | Internal/contributor |
| `src/rdp/telemetry/` | Structured runtime evidence. | Internal |
| `src/rune_decrypter_prime/utils/` | Focused tutorial and text utilities. | Internal/test support |
| `tutorials/v1/` | Active typed V1 examples and runner. | User-facing |
| `tests/` | Contract, regression, installation, and runtime tests. | Test-only |

## Public ownership

`src/rdp/api/__init__.py` defines the 32-symbol root. Its four subnamespace
modules define the rest of the exact 141-path contract. `src/rdp/__init__.py`
exposes the `api` module and does not mirror or forward API symbols.

Normal consumers use:

```python
from rdp import api
```

Internal consumers import the exact module that owns the required runtime
capability. There is no general internal facade or compatibility package.

## Engine ownership

Ciphers transform values for an already concrete key. Key operations own key
spaces and candidate manipulation. Solvers search. Scoring ranks candidates.
The core problem and engine packages connect those owners. AN3 does not move
those engine responsibilities into `rdp.api`.
