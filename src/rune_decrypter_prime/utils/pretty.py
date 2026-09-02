# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime

from rdp.data.runeglish import Runeglish

_MATCH_RATIO_THRESHOLD = 0.97

# Toggle to see a compact timeline of solver/optimizer events at the end
SHOW_TIMELINE = False

# ── helpers ──────────────────────────────────────────────────────────────────

def _as_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}

def _is_np_array(x: Any) -> bool:
    try:
        import numpy as np  # noqa: F401
        return hasattr(x, "dtype") and hasattr(x, "shape")
    except Exception:
        return False

def _to_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if _is_np_array(x):
        try:
            return x.tolist()
        except Exception:
            # last resort: iterate
            return [e for e in x]
    if isinstance(x, (list, tuple)):
        return list(x)
    # scalars → singleton
    return [x]

def _nonempty(x: Any) -> bool:
    if x is None:
        return False
    if _is_np_array(x):
        try:
            return x.size > 0
        except Exception:
            return True
    try:
        return len(x) > 0  # type: ignore[arg-type]
    except Exception:
        return True

def _preview_list(vals: Sequence[int] | Any, n: int = 32) -> str:
    xs = _to_list(vals)
    if not xs:
        return "[]"
    head = xs[:n]
    suffix = " …" if len(xs) > n else ""
    return f"[{', '.join(str(v) for v in head)}{suffix}]"

def _preview_text(s: Any, n: int = 180) -> str:
    if s is None:
        return ""
    if _is_np_array(s):
        try:
            s = "".join(map(str, s.tolist()))
        except Exception:
            s = str(s)
    else:
        s = str(s)
    return (s[:n] + "…") if len(s) > n else s

def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return default

def _latin_from_idx(idx: Sequence[int] | Any, wli: Optional[Sequence[Sequence[int]]], direction: Any = "ltr") -> str:
    """
    Robust: if WLI is missing or wrong length, still render Latin tokens
    without spacing. If WLI length matches idx, insert spaces accordingly.
    """
    try:
        arr = _to_list(idx)
        if not arr:
            return ""
        if not wli or len(wli) != len(arr):
            # No WLI → join latin tokens without spaces
            return "".join(Runeglish.pos_to_latin(int(p)) for p in arr)
        # WLI present and aligned → use word spacing
        return Runeglish.to_rune_latin(arr, wli, direction=direction)
    except Exception:
        return ""

def _runes_from_idx(idx: Sequence[int] | Any, wli: Optional[Sequence[Sequence[int]]]) -> str:
    try:
        return Runeglish.to_rune(_to_list(idx), wli if wli is not None else [])
    except Exception:
        return ""

def _latin_from_runes_str(runes: str) -> str:
    # per-rune char mapping; robust if Runeglish has the helper
    try:
        return " ".join(Runeglish.rune_to_latin(r) for r in runes)
    except Exception:
        return ""

def _find_last(events: List[Dict[str, Any]], typ: str) -> Optional[Dict[str, Any]]:
    for ev in reversed(events or []):
        if ev.get("type") == typ:
            return ev
    return None


def _normalize_rune_stream(text: Any) -> str:
    if text is None:
        return ""
    if _is_np_array(text):
        try:
            text = "".join(map(str, _to_list(text)))
        except Exception:
            text = str(text)
    return "".join(ch for ch in str(text) if not str(ch).isspace())


def _match_ratio_from_idx(found: Any, reference: Any) -> Optional[float]:
    ref_vals = _to_list(reference)
    if not ref_vals:
        return None
    cand_vals = _to_list(found)
    denom = max(len(ref_vals), len(cand_vals))
    if denom == 0:
        return None
    limit = min(len(ref_vals), len(cand_vals))
    matches = sum(1 for i in range(limit) if cand_vals[i] == ref_vals[i])
    return matches / float(denom)


def _match_ratio_from_runes(found: Any, reference: Any) -> Optional[float]:
    ref_norm = _normalize_rune_stream(reference)
    if not ref_norm:
        return None
    cand_norm = _normalize_rune_stream(found)
    denom = max(len(ref_norm), len(cand_norm))
    if denom == 0:
        return None
    limit = min(len(ref_norm), len(cand_norm))
    matches = sum(1 for i in range(limit) if cand_norm[i] == ref_norm[i])
    return matches / float(denom)

# ── main printer ─────────────────────────────────────────────────────────────
def print_run_report(
    *,
    title: str,
    cipher: Optional[str] = None,
    ct_rune: Optional[str] = None,
    solution: Any,
    match_ok: Optional[bool],
    app_version: Optional[str],
    beam_width: Optional[int] = None,
    key_idx: Sequence[int] = None,
    key_len: int = None,
    ct_idx: Sequence[int] = None,
    wli: Optional[Sequence[Sequence[int]]] = None,
    pt_rune_ref: Optional[str] = None,
    pt_idx_ref: Optional[Sequence[int]] = None,
    interruptors_ref: Optional[Sequence[int]] = None,
    verbose: bool = True,
    show_timeline: bool = False,   # default off to reduce clutter
    preview_len: int = 200,
    compact: bool = True,          # NEW: compact mode hides bulky sections
) -> None:
    """
    Pretty printer for a normalized Solution (post _ensure_plaintext_rune).
    - Compact mode: hides input blocks and prints a short meta summary.
    - Solver params are sanitized (only primitive, short values; drops nested 'name').
    """

    # ---- tiny, NumPy-safe helpers ------------------------------------------
    def _is_np_array(x):
        try:
            import numpy as _np
            return isinstance(x, _np.ndarray)
        except Exception:
            return False

    def _to_list(x):
        if x is None:
            return []
        if _is_np_array(x):
            return x.tolist()
        if isinstance(x, (list, tuple)):
            return list(x)
        return [x]

    def _nonempty(x):
        if x is None:
            return False
        if _is_np_array(x):
            return x.size > 0
        if isinstance(x, (list, tuple, dict, str)):
            return len(x) > 0
        return True

    def _compact_value(v, max_str=80):
        # allow only small, printable values
        if isinstance(v, (bool, int, float)):
            return v
        if isinstance(v, str):
            return v if len(v) <= max_str else (v[: max_str - 1] + "…")
        # everything else (lists, dicts, custom objects) is considered noisy
        return None

    def _compact_dict(d: Dict[str, Any], drop_keys: Sequence[str] = ()):
        out: Dict[str, Any] = {}
        for k, v in (d or {}).items():
            if k in drop_keys:
                continue
            cv = _compact_value(v)
            if cv is not None:
                out[k] = cv
        return out

    
    if not cipher:
        cipher = getattr(solution, "cipher_name", "") or cipher
    if ct_idx is None:
        ct_idx = getattr(solution, "ciphertext_idx", None)
    if not ct_rune:
        ct_rune = getattr(solution, "ciphertext_rune", "")
    if wli is None:
        wli = getattr(solution, "wli", None)

# ---- core fields (already normalized by _ensure_plaintext_rune) --------
    score      = _safe_float(getattr(solution, "score", None), None)
    found_key  = getattr(solution, "key", None)
    pt_idx     = _to_list(getattr(solution, "plaintext_idx", []))
    pt_runes   = str(getattr(solution, "plaintext_rune", "") or "")
    pt_latin_attr = str(getattr(solution, "plaintext_latin", "") or "")
    sol_wli    = getattr(solution, "wli", None)
    wli_for_latin = sol_wli if sol_wli is not None else wli
    direction = getattr(solution, "direction", "ltr")

    # ---- meta & telemetry ---------------------------------------------------
    meta    = _as_dict(getattr(solution, "meta", {}))
    m_solver = _as_dict(meta.get("solver", {}))
    m_work   = _as_dict(meta.get("work", {}))
    m_time   = _as_dict(meta.get("timings", {}))
    tel      = _as_dict(meta.get("telemetry", {}))
    events: List[Dict[str, Any]] = list(tel.get("events", []))

    _find_first = lambda es, t: next((ev for ev in (es or []) if ev.get("type") == t), None)
    first_s = _find_first(events, "solver_start") or _find_first(events, "optimizer_start")
    last_s  = _find_last(events, "solver_start")  or _find_last(events, "optimizer_start")
    last_e  = _find_last(events, "solver_end")    or _find_last(events, "optimizer_end")

    solver_name = (
        (m_solver.get("name") if isinstance(m_solver.get("name"), str) else None)
        or (first_s.get("name") if first_s and isinstance(first_s.get("name"), str) else None)
        or (last_s.get("name")  if last_s and isinstance(last_s.get("name"), str)  else None)
        or (last_e.get("name")  if last_e and isinstance(last_e.get("name"), str)  else None)
        or ""
    )

    # stop reason: prefer Solution field, then telemetry.run.result.reason, then solver span result
    run_block = _as_dict(tel.get("run", {}))
    run_result = _as_dict(run_block.get("result", {}))
    stop_reason = getattr(solution, "stop_reason", None)
    if stop_reason is None:
        stop_reason = run_result.get("reason")
    if stop_reason is None and solver_name:
        spans = _as_dict(tel.get("solver_spans", {}))
        span = _as_dict(spans.get(solver_name, {}))
        span_result = _as_dict(span.get("result", {}))
        stop_reason = span_result.get("reason")
    if stop_reason is None and last_e:
        stop_reason = last_e.get("reason")

    # params: meta wins; backfill from first start; sanitize & drop nested "name"
    solver_params_raw = dict(_as_dict(m_solver.get("params", {})))
    if first_s and isinstance(first_s.get("params"), dict):
        for k, v in first_s["params"].items():
            solver_params_raw.setdefault(k, v)
    if beam_width is not None:
        solver_params_raw.setdefault("beam_width", beam_width)

    solver_params = _compact_dict(solver_params_raw, drop_keys=("name",))


    # work: prefer meta, backfill from telemetry end events
    work = {k: v for k, v in m_work.items() if v is not None}

    def _merge_work(source):
        if not source:
            return
        mapping = {
            "candidates": "candidates",
            "attempted": "attempted",
            "parents": "parents",
            "kept": "kept",
            "evaluated": "evaluated",
            "accepted": "accepted",
            "accepts": "accepted",
            "pruned": "pruned",
            "generations": "generations",
            "rounds": "rounds",
            "iters": "iters",
            "step": "step",
            "tokens": "tokens",
            "tokens_processed": "tokens",
        }
        for src, dst in mapping.items():
            if dst not in work and src in source and source[src] is not None:
                work[dst] = source[src]

    _merge_work(last_e)
    run_end = _find_last(events, "run_end")
    _merge_work(run_end)
    work = {k: v for k, v in work.items() if v is not None}

    # timings
    timings = dict(m_time)
    if last_e:
        for src, dst in {"decrypt_time_s":"decrypt","score_time_s":"score","solve_time":"solve","elapsed_sec":"solve"}.items():
            if dst not in timings and src in last_e:
                timings[dst] = last_e[src]
    if run_end:
        if "decrypt" not in timings and run_end.get("decrypt_time_s") is not None:
            timings.setdefault("decrypt", run_end["decrypt_time_s"])
        if "score" not in timings and run_end.get("score_time_s") is not None:
            timings.setdefault("score", run_end["score_time_s"])
        if "tokens" not in work and run_end.get("tokens") is not None:
            work["tokens"] = run_end["tokens"]
    for src, dst in (("decrypt_time_s","decrypt"), ("score_time_s","score"), ("wall_time_s","solve")):
        if dst not in timings and src in tel:
            timings[dst] = tel[src]
    t_view: Dict[str, float] = {}
    for k in ("decrypt","score","solve"):
        if k in timings and timings[k] is not None:
            try: t_view[k] = float(timings[k])
            except Exception: pass
    total_time = (
        t_view.get("solve")
        or _safe_float(tel.get("wall_time_s"), None)
        or (last_e.get("elapsed_sec") if last_e else None)
    )
    if total_time is not None:
        try: t_view["total"] = float(total_time)
        except Exception: pass

    # scorer (compact)
    m_scr = _as_dict(meta.get("scorer", {})) or _as_dict(_as_dict(meta.get("telemetry", {})).get("scorer", {}))
    scorer_view = {}
    if m_scr:
        for k in ("name","objective","impl","device","dtype","score_mean","score_std","n_windows"):
            if k in m_scr:
                scorer_view[k] = m_scr[k]

    # ---- PT / CT previews ---------------------------------------------------
    pt_ref_runes = pt_rune_ref or ""
    pt_ref_latin = _latin_from_idx(_to_list(pt_idx_ref), wli_for_latin, direction) if _nonempty(pt_idx_ref) else ""
    if not pt_ref_latin and pt_ref_runes:
        try:
            pt_ref_latin = " ".join(Runeglish.rune_to_latin(ch) for ch in pt_ref_runes)
        except Exception:
            pt_ref_latin = ""

    pt_found_latin = pt_latin_attr if pt_latin_attr else (_latin_from_idx(pt_idx, wli_for_latin, direction) if _nonempty(pt_idx) else "")
    ct_idx_source = ct_idx if ct_idx is not None else getattr(solution, "ciphertext_idx", [])
    ct_idx_list   = _to_list(ct_idx_source)
    ct_latin_attr = getattr(solution, "ciphertext_latin", "") or ""
    ct_latin      = ct_latin_attr or (_latin_from_idx(ct_idx_list, wli_for_latin, direction) if ct_idx_list else "")
    ct_rune_attr  = getattr(solution, "ciphertext_rune", "") or ""
    ct_runes_disp = ct_rune or ct_rune_attr or _runes_from_idx(ct_idx_list, wli_for_latin)

    # ---- match ratio & recovered flag --------------------------------------
    match_ratio: Optional[float] = None
    if _nonempty(pt_idx_ref):
        match_ratio = _match_ratio_from_idx(pt_idx, pt_idx_ref)
    elif pt_ref_runes:
        match_ratio = _match_ratio_from_runes(pt_runes, pt_ref_runes)

    if match_ok is None and match_ratio is not None:
        match_ok = match_ratio >= _MATCH_RATIO_THRESHOLD

    # ---- interruptors (if solved) ------------------------------------------
    intr_meta = _as_dict(meta.get("interruptors", {}))
    intr_found_raw = intr_meta.get("found", None)
    intr_found = [int(v) for v in _to_list(intr_found_raw) if int(v) >= 0] if intr_found_raw is not None else None

    intr_expected: list[int] = []
    expected_known = False
    if interruptors_ref is not None:
        intr_expected = [int(v) for v in _to_list(interruptors_ref) if int(v) >= 0]
        expected_known = True
    elif "expected" in intr_meta:
        intr_expected = [int(v) for v in _to_list(intr_meta.get("expected")) if int(v) >= 0]
        expected_known = True
    else:
        core_len = intr_meta.get("core_length", None)
        if core_len is not None and key_idx is not None:
            try:
                core_len = int(core_len)
                key_vals = _to_list(key_idx)
                if len(key_vals) > core_len:
                    intr_expected = [int(v) for v in key_vals[core_len:] if int(v) >= 0]
                    expected_known = True
            except Exception:
                expected_known = False

    # ---- print --------------------------------------------------------------
    line = "-" * 72
    print(line)
    print(f"{title}  |  {_now_str()}")
    print(line)

    # Compact one-liner summary up top
    telemetry_present = bool(meta.get("telemetry"))

    summary_bits = []
    if cipher:          summary_bits.append(f"cipher={cipher}")
    if solver_name:     summary_bits.append(f"solver={solver_name}")
    if "tokens" in work:summary_bits.append(f"tokens={work['tokens']:,}")
    if "candidates" in work: summary_bits.append(f"candidates={work['candidates']:,}")
    if "iters" in work: summary_bits.append(f"iters={work['iters']}")
    if score is not None: summary_bits.append(f"score={score:.6f}")
    if stop_reason: summary_bits.append(f"stop={stop_reason}")
    if "total" in t_view:  summary_bits.append(f"total={t_view['total']:.3f}s")
    print("Summary     :", " | ".join(summary_bits) if summary_bits else "(no summary)")
    print(f"Telemetry   : {'Yes' if telemetry_present else 'No'}")

    # Keys (kept brief)
    if key_len is None and (isinstance(found_key, (list, tuple)) or _is_np_array(found_key)):
        try:
            key_len = len(found_key)
        except Exception:
            key_len = None
    if key_len is not None: print(f"Key length : {key_len}")
    if key_idx is not None: print(f"Key (nums) : {list(key_idx)}")
    if found_key is not None:
        fk = list(found_key) if isinstance(found_key, (list, tuple)) or _is_np_array(found_key) else found_key
        print(f"Key(found) : {fk}")

    if intr_found is not None:
        print(f"Interruptors(found): {intr_found}")
        if expected_known:
            print(f"Interruptors(real) : {intr_expected}")
            match = sorted(intr_found) == sorted(intr_expected)
            print(f"Interruptors match: {'Yes' if match else 'No'}")

    # Inputs (hidden in compact mode)
    if verbose and not compact:
        if pt_ref_runes: print(f"PT Ref (runes): {_preview_text(pt_ref_runes)}")
        if pt_ref_latin: print(f"PT Ref (latin): {_preview_text(pt_ref_latin)}")
        print(f"CT idx     : {_preview_list(ct_idx_list)}")
        print(f"CT runes   : {_preview_text(ct_runes_disp)}")
        if ct_latin:
            print(f"CT latin   : {_preview_text(ct_latin)}")

    # Outputs
    print(line)
    if pt_found_latin:
        print("Recovered plaintext (latin):")
        print(_preview_text(pt_found_latin, preview_len))
    if pt_runes:
        print("Recovered plaintext (runes):")
        print(_preview_text(pt_runes, preview_len))
    if _nonempty(pt_idx):
        print("Recovered plaintext (idx):")
        print(_preview_list(pt_idx))

    # Footer blocks
    recovered_label = "Unknown"
    if match_ok is True:
        recovered_label = "Yes"
    elif match_ok is False:
        recovered_label = "No"
    print(line)
    print(f"Recovered? : {recovered_label}")
    if match_ratio is not None:
        print(f"Match ratio: {match_ratio:.3f}")
    if score is not None:
        print(f"Score      : {score:.6f}")
    print(f"Stop reason: {stop_reason or 'Unknown'}")

    print("Scorer     :", scorer_view if scorer_view else {})

    solver_view = {"name": solver_name}
    # merge sanitized params (no 'name' collision, no huge objects)
    solver_view.update({k: v for k, v in sorted(solver_params.items())})
    print("Solver     :", solver_view if any(v is not None for v in solver_view.values()) else {})

    def _first_non_none(*vals):
        for v in vals:
            if v is None:
                continue
            return v
        return None

    work_summary: Dict[str, Any] = {}
    dec_time = _first_non_none(
        work.get("decrypt_time_s"),
        t_view.get("decrypt"),
        (last_e or {}).get("decrypt_time_s"),
        (run_end or {}).get("decrypt_time_s"),
        tel.get("decrypt_time_s"),
    )
    if dec_time is not None:
        try:
            work_summary["decrypt_time_s"] = float(dec_time)
        except Exception:
            pass
    score_time = _first_non_none(
        work.get("score_time_s"),
        t_view.get("score"),
        (last_e or {}).get("score_time_s"),
        (run_end or {}).get("score_time_s"),
        tel.get("score_time_s"),
    )
    if score_time is not None:
        try:
            work_summary["score_time_s"] = float(score_time)
        except Exception:
            pass
    evals_val = _first_non_none(
        work.get("evals"),
        work.get("candidates"),
        (last_e or {}).get("candidates"),
        (run_end or {}).get("candidates"),
        tel.get("candidates_evaluated"),
    )
    if evals_val is not None:
        try:
            work_summary["evals"] = int(evals_val)
        except Exception:
            pass
    tokens_val = _first_non_none(
        work.get("tokens"),
        tel.get("tokens_processed"),
        (run_end or {}).get("tokens"),
    )
    if tokens_val is not None:
        try:
            work_summary["tokens"] = int(tokens_val)
        except Exception:
            pass

    print("Work       :", work_summary if work_summary else (work if work else {}))
    print("Timings (s):", t_view if t_view else {})

    # Timeline (optional, still compact)
    if show_timeline and events:
        print(line)
        print("Timeline   :")
        for ev in events:
            t = ev.get("type"); nm = ev.get("name", "")
            if t in ("solver_start","optimizer_start"):
                ps = _as_dict(ev.get("params", {}))
                print(f"  start  {nm}  params={_compact_dict(ps)}")
            elif t in ("solver_progress","optimizer_progress"):
                best = ev.get("best") or ev.get("best_score")
                step = ev.get("step") or ev.get("gen") or ev.get("round")
                kept = ev.get("kept")
                msg = f"  prog   {nm}"
                if step is not None: msg += f"  step={step}"
                if best is not None: msg += f"  best={best}"
                if kept is not None: msg += f"  kept={kept}"
                print(msg)
            elif t in ("solver_end","optimizer_end"):
                kept = ev.get("kept"); cand = ev.get("candidates"); tok = ev.get("tokens")
                solve = ev.get("solve_time") or ev.get("elapsed_sec")
                parts = [f"  end    {nm}"]
                if kept is not None: parts.append(f"kept={kept}")
                if cand is not None: parts.append(f"cand={cand}")
                if tok  is not None: parts.append(f"tok={tok}")
                if solve is not None: parts.append(f"solve={solve}")
                print("  ".join(parts))

    print(line)
    if app_version:
        print(f"App version: {app_version}")
        print(line)

# #     print("─" * 60)
