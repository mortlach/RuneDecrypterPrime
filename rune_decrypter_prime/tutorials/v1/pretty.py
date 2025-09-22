# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime

from rune_decrypter_prime.utils.runeglish import Runeglish

# --- helpers ---------------------------------------------------------------

def _as_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}

def _meta_get(meta: Dict[str, Any], key: str, default: Any = None) -> Any:
    """meta[key] may be a dict, string, or absent."""
    val = meta.get(key, default)
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        return {"name": val}
    return default if val is None else val

def _preview_list(vals: Sequence[int], n: int = 32) -> str:
    if not vals:
        return "[]"
    head = list(vals[:n])
    suffix = " …" if len(vals) > n else ""
    return f"{head}{suffix}"

def _preview_text(s: str, n: int = 180) -> str:
    if not s:
        return ""
    return (s[:n] + "…") if len(s) > n else s

def _latin_from_idx(idx: Sequence[int], wli: Optional[Sequence[Sequence[int]]]) -> str:
    """Convert GP indices into canonical Latin string using Runeglish."""
    try:
        return Runeglish.to_rune_latin(idx, wli if wli is not None else [])
    except Exception:
        return ""

def _runes_from_idx(idx: Sequence[int], wli: Optional[Sequence[Sequence[int]]]) -> str:
    """Convert GP indices into rune string using Runeglish."""
    try:
        return Runeglish.to_rune(idx, wli if wli is not None else [])
    except Exception:
        return ""
#
# def _latin_from_runestr(runetext: str) -> str:
#     out: List[str] = []
#     for ch in runetext:
#         out.append(" " if ch == " " else str(Runeglish.rune2latincanon(ch)))
#     return "".join(out)

def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return default

def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --- main printer ----------------------------------------------------------

def print_run_report(
    *,
    title: str,
    cipher: str,
    key_idx: Sequence[int],
    ct_idx: Sequence[int],
    ct_rune: str,
    solution: Any,
    match_ok: bool,
    app_version: Optional[str],
    key_len: int,
    beam_width: Optional[int] = None,
    wli: Optional[Sequence[Sequence[int]]] = None,
    pt_rune_ref: Optional[str] = None,
    pt_idx_ref: Optional[Sequence[int]] = None,
) -> None:
    """
    Pretty tutorial printer with live optimizer telemetry.
    """

    score = _safe_float(getattr(solution, "score", None), None)
    meta  = _as_dict(getattr(solution, "meta", {}))
    found_key = getattr(solution, "key", None)

    # Extract optimizer/scorer/work/timings blocks
    m_opt = _meta_get(meta, "optimizer", {})
    m_scr = _meta_get(meta, "scorer", {}) or _as_dict(meta.get("telemetry", {})).get("scorer", {})
    m_wrk = _as_dict(meta.get("work", {}))
    m_tim = _as_dict(meta.get("timings", {}))

    # Pull telemetry optimizer node if present
    tel_opt_all = _as_dict(meta.get("telemetry", {})).get("optimizer", {})
    tel_node: Dict[str, Any] = {}
    if isinstance(tel_opt_all, dict) and tel_opt_all:
        # if meta.optimizer has a name, try that; else take first
        opt_name_guess = _as_dict(m_opt).get("name")
        if opt_name_guess and opt_name_guess in tel_opt_all:
            tel_node = _as_dict(tel_opt_all[opt_name_guess])
        else:
            # take first optimizer node if we don't know the name
            first = next(iter(tel_opt_all.values()), {})
            tel_node = _as_dict(first)

    pt_ref_runes = pt_rune_ref or ""
    pt_ref_latin = ""
    if pt_idx_ref and len(pt_idx_ref) > 0:
        pt_ref_latin = Runeglish.to_rune_latin(pt_idx_ref, wli)
        pt_ref_runes = Runeglish.to_rune(pt_idx_ref, wli)
    elif pt_ref_runes:
        pt_ref_latin = "".join(Runeglish.rune_to_latin(r) for r in pt_ref_runes)

    pt_found_latin, pt_found_runes = "", ""
    pt_found_idx = getattr(solution, "plaintext_idx", None)
    if isinstance(pt_found_idx, (list, tuple)) and pt_found_idx:
        pt_found_latin = Runeglish.to_rune_latin(pt_found_idx, wli)
        pt_found_runes = Runeglish.to_rune(pt_found_idx, wli)
    else:
        pt_raw = getattr(solution, "plaintext", "")
        if isinstance(pt_raw, str) and pt_raw:
            # assume rune string
            pt_found_runes = pt_raw
            pt_found_latin = "".join(Runeglish.rune_to_latin(r) for r in pt_raw)

    ct_latin, ct_runes = "", ""
    try:
        ct_latin = Runeglish.to_rune_latin(ct_idx, wli)
        ct_runes = Runeglish.to_rune(ct_idx, wli)
    except Exception:
        pass

    # Header
    print("─" * 60)
    print(f"{title}  |  {_now_str()}")
    print("─" * 60)
    if cipher  is not None: print(f"Cipher     : {cipher}")
    if key_len is not None: print(f"Key length : {key_len}")
    if key_idx is not None: print(f"Key (nums) : {list(key_idx)}")
    if found_key is not None:
        print(f"Key(found) : {list(found_key) if isinstance(found_key, (list, tuple)) else found_key}")

    if pt_ref_runes:
        print(f"PT (runes) : {_preview_text(pt_ref_runes)}")
    if pt_ref_latin:
        print(f"PT (latin) : {_preview_text(pt_ref_latin)}")


    print(f"CT idx     : {_preview_list(ct_idx)}")
    print(f"CT runes   : {_preview_text(ct_runes)}")
    if ct_latin:
        print(f"CT latin   : {_preview_text(ct_latin)}")

    if pt_found_latin:
        print("─" * 60)
        print("Recovered plaintext (latin):")
        print(_preview_text(pt_found_latin, 360))
    if pt_found_runes:
        print("Recovered plaintext (runes):")
        print(_preview_text(pt_found_runes, 360))

    # print(f"CT runes   : {_preview_text(ct_rune)}")
    # if ct_latin:
    #     print(f"CT latin   : {_preview_text(ct_latin)}")
    #
    # if pt_found_latin:
    #     print("─" * 60)
    #     print("Recovered plaintext (latin):")
    #     print(_preview_text(pt_found_latin, 360))

    # Footer
    print("─" * 60)
    print(f"Recovered? : {'Yes' if match_ok else 'No'}")
    if score is not None:
        print(f"Score      : {score:.6f}")

    # Scorer block
    m_scr = _meta_get(meta, "scorer", {})
    if not m_scr:
        m_scr = _as_dict(meta.get("telemetry", {})).get("scorer", {})
    scr_name = _as_dict(m_scr).get("name", "")
    scr_obj = _as_dict(m_scr).get("objective", "")
    print("Scorer     :", {"name": scr_name, "objective": scr_obj} if (scr_name or scr_obj) else {})

    # Optimizer block (merge SolveSpec + telemetry node)
    opt_name = _as_dict(m_opt).get("name") or (m_opt if isinstance(m_opt, str) else tel_node.get("name", ""))
    opt_params = dict(_as_dict(m_opt).get("params", {}))
    if "params" in tel_node:
        opt_params.update(_as_dict(tel_node.get("params", {})))
    print("Optimizer  :", {"name": opt_name, **opt_params} if opt_name or opt_params else {})

    # Work block
    work = {}
    for k in ("len_plaintext", "tokens", "attempted_total", "kept_total", "pruned_total"):
        if k in m_wrk:
            work[k] = m_wrk[k]
        if k in tel_node:
            work[k] = tel_node[k]
    print("Work       :", work if work else {})

    # Timings
    timings = {}
    for k in ("decrypt", "score", "solve", "elapsed_sec"):
        if k in m_tim:
            timings[k] = m_tim[k]
        if k in tel_node:
            timings[k] = tel_node[k]
    print("Timings    :", timings if timings else {})

    print("─" * 60)
    print("Note: Higher scores indicate outputs that look more like language")
    print("      (n-gram log-probabilities, often averaged over a window).")
    if app_version:
        print("─" * 60)
        print(f"App version: {app_version}")
    print("─" * 60)

def print_telemetry(sol):
    from rune_decrypter_prime.utils.telemetry_utils import telem, run_meta, get, print_telem

    # after you have `sol = run.solve(...)`:
    print("score:", sol.score)
    print("device:", get(telem(sol), "device"))
    print("scorer.impl:", get(telem(sol), "scorer.impl"))
    print("optimizer.name:", get(telem(sol), "optimizer.name"))
    print("optimizer.params.pop_size:", get(telem(sol), "optimizer.params.pop_size"))
    print("tokens processed:", get(run_meta(sol), "tokens"))

    # or dump everything:
    print("--- telemetry dump ---")
    print_telem(sol)

    # or only specific fields:
    print_telem(sol, only=[
        "device",
        "scorer.impl",
        "scorer.direction",
        "optimizer.name",
        "optimizer.params",
        "candidates_evaluated",
        "tokens_processed",
        "decrypt_time",
        "score_time",
    ])

