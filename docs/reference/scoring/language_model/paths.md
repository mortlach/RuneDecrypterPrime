# `scoring/language_model/paths.py`

> Purpose: resolve and validate the filesystem paths for LMPrime assets. Allows scorers to run out of the box (using bundled models) or point to custom models when advanced users provide a `model_root`.

## Functions
| Helper | Description |
| --- | --- |
| `_coerce_model_root(value)` | Accepts `None`, string, or `Path`, returning an absolute path under the package's LM root. |
| `resolve_lm_root(cfg)` | Looks at `cfg.model_root` (or mapping) and falls back to `default_lm_root()`. |
| `load_index(root)` | Reads `<root>/index.json` to find model metadata (char/WLI availability, versions). |
| `default_lm_root()` | Returns the package-relative directory that ships with the repo; keep aligned with release artifacts. |

## Usage
Called by `LanguageModelPrime` during initialisation. Tutorials rarely interact with this module directly unless they bundle custom LM assets.

