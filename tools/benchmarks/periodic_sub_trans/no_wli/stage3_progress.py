from __future__ import annotations

import time
from typing import Any, Dict, List

import numpy as np


def as_nonneg_float(v: Any) -> float:
    try:
        f = float(v)
    except Exception:
        return 0.0
    if not np.isfinite(f):
        return 0.0
    return float(max(0.0, f))


def span_counter_summary_from_obj(obj: Any) -> Dict[str, float]:
    src = obj if isinstance(obj, dict) else {}
    return dict(
        total=as_nonneg_float(src.get("span_hamming_eval_total", 0)),
        active=as_nonneg_float(src.get("span_hamming_eval_active", 0)),
        skipped=as_nonneg_float(src.get("span_hamming_eval_skipped_char_gate", 0)),
        seconds_total=as_nonneg_float(src.get("span_hamming_eval_seconds_total", 0.0)),
        seconds_active=as_nonneg_float(src.get("span_hamming_eval_active_seconds_total", 0.0)),
    )


def span_counter_delta(*, before: Dict[str, float], after: Dict[str, float]) -> Dict[str, float]:
    keys = ("total", "active", "skipped", "seconds_total", "seconds_active")
    out: Dict[str, float] = {}
    for k in keys:
        out[k] = float(max(0.0, as_nonneg_float(after.get(k, 0.0)) - as_nonneg_float(before.get(k, 0.0))))
    return out


def solution_span_counter_summary(sol: Any) -> Dict[str, float]:
    """Read span-hamming counters from solver-result telemetry (inner-loop truth)."""
    tele: Dict[str, Any] = {}
    try:
        meta = getattr(sol, "meta", {}) or {}
        if isinstance(meta, dict):
            t_obj = meta.get("telemetry", {})
            if isinstance(t_obj, dict):
                tele = dict(t_obj)
    except Exception:
        tele = {}
    scorer_tele = tele.get("scorer", {}) if isinstance(tele.get("scorer", {}), dict) else {}
    src = tele if "span_hamming_eval_total" in tele else scorer_tele
    return span_counter_summary_from_obj(src)


def scorer_span_counter_summary(scorer: Any) -> Dict[str, float]:
    """Read cumulative span-hamming counters from a scorer runtime."""
    tele: Dict[str, Any] = {}
    try:
        if hasattr(scorer, "telemetry") and callable(scorer.telemetry):
            t_obj = scorer.telemetry()
            if isinstance(t_obj, dict):
                tele = dict(t_obj)
    except Exception:
        tele = {}
    scorer_tele = tele.get("scorer", {}) if isinstance(tele.get("scorer", {}), dict) else {}
    src = tele if "span_hamming_eval_total" in tele else scorer_tele
    return span_counter_summary_from_obj(src)


def fmt_finite_float(value: Any, *, digits: int = 6) -> str:
    try:
        f = float(value)
    except Exception:
        return "nan"
    if not np.isfinite(f):
        return "nan"
    return f"{f:.{int(max(0, digits))}f}"


def stage3_progress_logging(
    *,
    tier_name: str,
    text_id: int,
    key_seed: int,
    phase: str,
    phase_steps: int,
    phase_start_ts: float,
    heartbeat_seconds: float,
    heartbeat_state: Dict[str, Any] | None = None,
    min_step: int = 0,
    min_elapsed_seconds: float = 0.0,
    evals_base: int = 0,
    phaseA_done: int | None = None,
    phaseA_total: int | None = None,
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    """Return a lightweight progress callback config for Stage-3 heartbeat lines."""
    heartbeat = float(max(1.0, heartbeat_seconds))
    steps_planned = int(max(0, phase_steps))
    t0 = float(phase_start_ts)
    hb_state = heartbeat_state if isinstance(heartbeat_state, dict) else {}
    if "last_emit_ts" not in hb_state:
        hb_state["last_emit_ts"] = float("-inf")
    min_step_i = int(max(0, min_step))
    min_elapsed_s = float(max(0.0, min_elapsed_seconds))
    evals_offset = int(max(0, int(evals_base)))

    def _cb(payload: Dict[str, Any], _key_preview: List[int] | None = None) -> None:
        now = float(time.time())
        p = payload if isinstance(payload, dict) else {}
        step_v = p.get("step", None)
        pct_v = p.get("pct", None)
        evals_v = p.get("evals", None)
        step_i = int(step_v) if isinstance(step_v, (int, float)) else -1
        elapsed_s = max(0.0, now - t0)
        if step_i >= 0 and step_i < min_step_i and elapsed_s < min_elapsed_s:
            return
        if (now - float(hb_state.get("last_emit_ts", float("-inf")))) < heartbeat:
            return
        hb_state["last_emit_ts"] = now

        step_txt = "n/a"
        if step_i >= 0:
            step_txt = f"{step_i}/{steps_planned}" if steps_planned > 0 else f"{step_i}"
        pct_txt = f"{int(pct_v)}" if isinstance(pct_v, (int, float)) else "n/a"
        evals_i = int(evals_v) if isinstance(evals_v, (int, float)) else -1
        evals_txt = str(int(evals_offset + evals_i)) if evals_i >= 0 else "n/a"
        elapsed_min = max(0.0, (now - t0) / 60.0)
        best_pct = float(p.get("best_score", float("nan")))
        best_raw = float(p.get("best_raw", float("nan")))
        if np.isfinite(best_pct):
            hb_state["best_pct"] = float(
                max(float(hb_state.get("best_pct", float("-inf"))), float(best_pct))
            )
        if np.isfinite(best_raw):
            hb_state["best_raw"] = float(
                max(float(hb_state.get("best_raw", float("-inf"))), float(best_raw))
            )
        best_pct_txt = fmt_finite_float(hb_state.get("best_pct", best_pct))
        best_raw_txt = fmt_finite_float(hb_state.get("best_raw", best_raw))
        phase_txt = str(phase)
        if phaseA_total is not None and int(phaseA_total) > 0:
            done_v = int(max(0, int(phaseA_done if phaseA_done is not None else 0)))
            total_v = int(max(1, int(phaseA_total)))
            phase_txt = f"phaseA done={done_v}/{total_v}"
        print(
            f"{log_prefix} stage3-heartbeat tier={tier_name} text={int(text_id)} key_seed={int(key_seed)} "
            f"phase={phase_txt} t={elapsed_min:.1f}m step={step_txt} pct={pct_txt} evals={evals_txt} "
            f"best_search_avg={best_pct_txt} best_search_raw={best_raw_txt}",
            flush=True,
        )

    return dict(progress_callback=_cb, log_interval=1)
