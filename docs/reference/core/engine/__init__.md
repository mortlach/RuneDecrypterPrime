# `core/engine/__init__.py`

> Purpose: lightweight re-export surface pointing to `core/engine/engine.py`.

 Simple re-export module that exposes `EngineConfig` and `solve` from `core/engine/engine.py`. The `__getattr__` shim is there to keep legacy imports (`from rune_decrypter_prime.core.engine import solve`) working without eagerly importing heavy solver classes.

No additional API beyond the re-export, so refer to `docs/reference/core/engine/engine.md` for details.

