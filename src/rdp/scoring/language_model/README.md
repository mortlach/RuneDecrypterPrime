# Language-model runtime

Load rune and word-location n-gram tables and their calibration data for scoring.

## Where to look

- [language_model_prime_runtime.py](language_model_prime_runtime.py) — LmPrimeRuntime, buckets and ECDF cache.
- [language_model_prime.py](language_model_prime.py) — LanguageModelPrime access and sentence scoring.
- [paths.py](paths.py) — Model-root and index resolution.
- [load_status.py](load_status.py) — Structured model-loading status.
- [ecdf_validator.py](ecdf_validator.py) — Validate calibration arrays and metadata.
- [fastlm.cpp](fastlm.cpp) — Native table-loading implementation.
- [setup_fastlm.py](setup_fastlm.py) — Build entry point for the native loader.

## Choices and extension

Choose model orders and objectives through scoring configuration. Order, direction and calibration must agree with the selected assets. The bundled set supports short examples; full LM assets are a separate installation. Do not fix missing models by silently selecting different evidence.

Continue with the [guide](../../../../docs/setup/installation.md) or the [package map](../../README.md).
