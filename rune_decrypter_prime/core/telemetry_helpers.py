# ============================================================
# rune_decrypter_prime/core/telemetry_helpers.py
# Helper functions/context manager for optimiser telemetry nodes.
# ============================================================
from __future__ import annotations
from typing import Any, Dict, Optional
import time
from contextlib import AbstractContextManager

try:
    from rune_decrypter_prime.io.run_logger import get_logger
    _LOGGER = get_logger()
except Exception:
    _LOGGER = None


def _opt_node(problem, name: str) -> Optional[Dict[str, Any]]:
    """
    Return (and create if needed) the telemetry node for a given optimiser.

    Node shape after a run:
      {
        "params": {...},          # from opt_start
        "steps": [ {...}, ... ],  # from opt_progress
        "pruned_total": int,      # aggregated
        "elapsed_sec": float,     # set in opt_end
        "best_score": float,      # set in opt_end (if provided)
        "depth_reached": int,     # derived from steps in opt_end
        "attempted_total": int,   # derived from steps in opt_end
        "kept_total": int,        # derived from steps in opt_end
        "nodes_per_sec": float,   # derived in opt_end
      }
    """
    t = getattr(problem, "telemetry", None)
    if t is None:
        return None
    if not hasattr(t, "optimizer") or t.optimizer is None:
        # Telemetry is a dataclass; ensure optimizer dict exists
        try:
            t.optimizer = {}  # type: ignore[attr-defined]
        except Exception:
            return None
    node = t.optimizer.get(name)  # type: ignore[attr-defined]
    if node is None:
        node = {"params": {}, "steps": [], "pruned_total": 0}
        t.optimizer[name] = node  # type: ignore[attr-defined]
    return node


def opt_start(problem, name: str, params: Dict[str, Any]) -> None:
    """
    Called once per optimiser run to record initial parameters.
    Also emits a structured event to the run logger, if present.
    """
    node = _opt_node(problem, name)
    if node is not None:
        node["params"] = dict(params or {})
        node.setdefault("steps", [])
        node.setdefault("pruned_total", 0)
    if _LOGGER:
        _LOGGER.log_event({"type": "optimizer_start", "name": name, "params": dict(params or {})})


def opt_progress(problem, name: str, step: Dict[str, Any]) -> None:
    """
    Record a single progress snapshot from the optimiser.
    Expected keys may include: depth/iter, attempted, kept, pruned, top/best, etc.
    """
    node = _opt_node(problem, name)
    if node is not None:
        steps = node.setdefault("steps", [])
        steps.append(dict(step or {}))
        # Keep a running total of pruned if available
        pruned = int(step.get("pruned", 0)) if isinstance(step, dict) else 0
        node["pruned_total"] = int(node.get("pruned_total", 0)) + pruned
    if _LOGGER:
        _LOGGER.log_event({"type": "optimizer_progress", "name": name, **dict(step or {})})


def opt_end(problem, name: str, result: Dict[str, Any], t0: float) -> None:
    """
    Called once on completion to close the span. Computes elapsed time and
    derives small summary counters from the recorded steps.
    """
    elapsed_sec = float(time.perf_counter() - float(t0))
    node = _opt_node(problem, name)
    if node is not None:
        # Persist elapsed time
        node["elapsed_sec"] = elapsed_sec
        # Persist any provided result fields (e.g., pruned_total, best_score)
        for k, v in dict(result or {}).items():
            if k == "pruned_total":
                node["pruned_total"] = int(node.get("pruned_total", 0)) + int(v or 0)
            else:
                node[k] = v

        # Derive simple aggregates from steps
        steps = node.get("steps", [])
        if isinstance(steps, list) and steps:
            try:
                depth_reached = max(int(s.get("depth", 0)) for s in steps if isinstance(s, dict))
            except Exception:
                depth_reached = 0
            try:
                attempted_total = sum(int(s.get("attempted", 0)) for s in steps if isinstance(s, dict))
            except Exception:
                attempted_total = 0
            try:
                kept_total = sum(int(s.get("kept", 0)) for s in steps if isinstance(s, dict))
            except Exception:
                kept_total = 0
        else:
            depth_reached = 0
            attempted_total = 0
            kept_total = 0

        node["depth_reached"] = depth_reached
        node["attempted_total"] = attempted_total
        node["kept_total"] = kept_total
        node["nodes_per_sec"] = (attempted_total / elapsed_sec) if elapsed_sec > 0.0 else 0.0

    if _LOGGER:
        _LOGGER.log_event({
            "type": "optimizer_end",
            "name": name,
            "elapsed_sec": elapsed_sec,
            **(dict(result or {})),
        })


def attach_telemetry_to_meta(problem, meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach problem.telemetry.to_dict() into meta["telemetry"] and return meta.
    """
    try:
        t = getattr(problem, "telemetry", None)
        if t is None:
            return meta
        tel = t.to_dict() if hasattr(t, "to_dict") else dict(t)  # defensive
        meta = dict(meta or {})
        meta["telemetry"] = tel
        return meta
    except Exception:
        return meta


# -------- Optional, non-breaking convenience API for optimisers --------

class TelemetrySpan(AbstractContextManager):
    """
    with TelemetrySpan(problem, name="beam", params={...}) as span:
        ...
        span.progress(depth=..., attempted=..., kept=..., pruned=..., top=...)
        ...
        span.end(pruned_total=..., best_score=...)

    Automatically computes elapsed time and populates the telemetry node via
    opt_start/opt_progress/opt_end. Also mirrors events to RunLogger if present.
    """
    def __init__(self, problem, name: str, params: Dict[str, Any] | None = None):
        self.problem = problem
        self.name = name
        self.params = dict(params or {})
        self._t0: Optional[float] = None
        self._ended: bool = False

    def __enter__(self):
        self._t0 = time.perf_counter()
        opt_start(self.problem, self.name, self.params)
        return self

    def progress(self, **step):
        opt_progress(self.problem, self.name, dict(step))

    def end(self, **result):
        if not self._ended and self._t0 is not None:
            opt_end(self.problem, self.name, dict(result), self._t0)
            self._ended = True

    def __exit__(self, exc_type, exc, tb):
        # If an exception happens, still close out the span with an 'error' result.
        if not self._ended and self._t0 is not None:
            if exc:
                self.end(error=str(exc))
            else:
                self.end()
        return False  # don't suppress exceptions
