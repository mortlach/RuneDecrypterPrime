# `core/solver_engine.py`

> Purpose: legacy shim retained for backwards compatibility; prefer `core/engine/engine.py`.

> Legacy shim kept for backwards compatibility. Historically, `core/solver_engine.py` exposed `_solver_kind_from_cfg` and routed to the old solver implementations. In v1 all functionality moved to `core/engine/engine.py`, so this module simply re-exports helpers to keep imports alive.

Prefer the new API under `core/engine/engine.py`. See that reference page for modern usage and tests.

