# rune_decrypter_prime/telemetry/events.py
from __future__ import annotations
import copy
import time
from typing import Any, Dict

def _ensure_tel_dict(problem) -> Dict[str, Any] | None:
    """
    Ensure problem.telemetry exists and is a dict.
    Return it (or None if we can't).
    """
    try:
        tel = getattr(problem, "telemetry", None)
        if tel is None or not isinstance(tel, dict):
            tel = {}
            setattr(problem, "telemetry", tel)
        return tel
    except Exception:
        return None

# ---- New solver-* API (preferred names) ------------------------------------

def solver_start(problem, name: str, params: Dict[str, Any] | None = None) -> None:
    tel = _ensure_tel_dict(problem)
    if tel is None:
        return
    now = time.time()
    spans = tel.setdefault("solver_spans", {})
    this = spans.setdefault(str(name), {})
    this.setdefault("params", dict(params or {}))
    this.setdefault("start_ts", now)
    # Compat breadcrumb for old consumers
    this.setdefault("optimizer", str(name))
    this["solver"] = str(name)

def solver_progress(problem, name: str, **payload) -> None:
    tel = _ensure_tel_dict(problem)
    if tel is None:
        return
    prog = tel.setdefault("solver_progress", [])
    item = dict(payload or {})
    item.setdefault("solver", str(name))
    # Compat breadcrumb
    item.setdefault("optimizer", str(name))
    prog.append(item)

def solver_end(problem, name: str, result: Dict[str, Any] | None, t0: float) -> None:
    tel = _ensure_tel_dict(problem)
    if tel is None:
        return
    now = time.perf_counter()
    spans = tel.setdefault("solver_spans", {})
    this = spans.setdefault(str(name), {})
    this.setdefault("solver", str(name))
    # Compat breadcrumb
    this.setdefault("optimizer", str(name))
    if isinstance(result, dict):
        # Prefer solver_* names; also mirror into legacy keys if they exist in downstream tools
        this.setdefault("result", {})
        this["result"].update(result)
    try:
        dur = max(0.0, float(now - float(t0)))
        this["duration_s"] = dur
    except Exception:
        pass

# ---- Back-compat aliases (old optimizer_* names) ---------------------------

optimizer_start = solver_start
optimizer_progress = solver_progress
optimizer_end = solver_end

# ---- Solution/meta hook (unchanged) ---------------------------------------

def attach_telemetry_to_meta(sol, problem) -> None:
    """
    Attach problem.telemetry into sol.meta['telemetry'] (best-effort).
    """
    try:
        meta = getattr(sol, "meta", None)
        if not isinstance(meta, dict):
            return
        existing = meta.get("telemetry", {})
        tel = dict(existing) if isinstance(existing, dict) else {}
        p_tel = getattr(problem, "telemetry", None)
        if isinstance(p_tel, dict):
            p_copy = copy.deepcopy(p_tel)
            for k, v in p_copy.items():
                tel.setdefault(k, v)
        meta["telemetry"] = tel
        run = tel.get("run", {})
        if "seed" not in tel and isinstance(run, dict) and "seed" in run:
            tel["seed"] = run.get("seed")
        if "wall_time_s" not in tel and isinstance(run, dict):
            try:
                start = float(run.get("start_ts"))
                end = float(run.get("end_ts"))
                tel["wall_time_s"] = max(0.0, end - start)
            except Exception:
                pass
        if "optimizer" not in tel:
            solver_block = tel.get("solver")
            if isinstance(solver_block, dict):
                tel["optimizer"] = solver_block
            elif isinstance(run, dict) and "solver" in run:
                tel["optimizer"] = {"name": run.get("solver")}
        if "pipeline" not in tel and isinstance(run, dict) and "pipeline" in run:
            tel["pipeline"] = run.get("pipeline")
        scorer_block = tel.get("scorer")
        if not isinstance(scorer_block, dict):
            scorer_block = {}
            tel["scorer"] = scorer_block
        run_scorer = run.get("scorer") if isinstance(run, dict) else None
        if isinstance(run_scorer, dict):
            for key in ("impl", "device", "dtype"):
                val = run_scorer.get(key)
                if key not in scorer_block and val is not None:
                    scorer_block[key] = val
    except Exception:
        pass


# ---- Run-level envelope (Stage-2) ------------------------------------------

def run_start(*, problem, seed, solver, device, scorer, pipeline, params=None) -> None:
    tel = getattr(problem, "telemetry", None)
    try:
        tel = tel.to_dict() if hasattr(tel, "to_dict") else tel
    except Exception:
        pass
    if not isinstance(tel, dict):
        return
    run: Dict[str, Any] = {
        "seed": int(seed) if seed is not None else None,
        "solver": str(solver),
        "device": str(device),
        "start_ts": time.time(),
    }
    if isinstance(scorer, dict):
        run["scorer"] = dict(scorer)
    if isinstance(pipeline, dict):
        run["pipeline"] = dict(pipeline)
    if isinstance(params, dict):
        run["params"] = dict(params)
    tel["run"] = run

def run_end(*, problem, seed, solver, device, scorer, pipeline, result=None) -> None:
    tel = getattr(problem, "telemetry", None)
    try:
        tel = tel.to_dict() if hasattr(tel, "to_dict") else tel
    except Exception:
        pass
    if not isinstance(tel, dict):
        return
    run = tel.setdefault("run", {})
    if "end_ts" in run:
        return
    run["end_ts"] = time.time()
    if isinstance(result, dict):
        run["result"] = dict(result)

# Back-compat aliases if callers used older names
log_run_start = run_start
log_run_end = run_end

