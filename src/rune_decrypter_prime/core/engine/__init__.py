# Minimal, stable surface for Stage-2 engine
__all__ = ["EngineConfig", "solve"]


def __getattr__(name):
    if name in {"EngineConfig", "solve"}:
        from .engine import EngineConfig, solve  # local import to avoid circulars

        return {"EngineConfig": EngineConfig, "solve": solve}[name]
    raise AttributeError(name)
