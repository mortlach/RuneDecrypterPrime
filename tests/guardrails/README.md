# Guardrails tests

Static ownership, enum-normalisation and dependency boundaries. These catch
architectural drift without treating the physical layout as the public API.

Useful entry points: [test_core_no_backend_optimizer_magic_literals.py](test_core_no_backend_optimizer_magic_literals.py), [test_core_no_direction_magic_tokens.py](test_core_no_direction_magic_tokens.py), [test_core_no_legacy_scorer_dir_leak.py](test_core_no_legacy_scorer_dir_leak.py).

See [test selection and tiers](../../docs/tests_docs/tiering.md) for the wider testing context.
