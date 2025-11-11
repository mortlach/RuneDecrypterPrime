# ============================================================
# tests/harness.py   (unified test runner)
# ============================================================
"""
Roundtrip harness for cipher tests.

This function drives a full cycle:
  • Encrypt plaintext with random key
  • Build configs (cipher/scoring/optimizer/logging)
  • Solve using the configured optimizer
  • Validate decryption correctness
  • Log run telemetry + optional cProfile trace
  • Return (known_key, found_key, sol.meta)

Unified logging:
  - Uses rune_decrypter_prime.io.run_logger.RunLogger
  - All events (start/end/errors/trace) go to JSONL in output/<kind>/<run_id>/logs/
  - Trace logs also go to output/<kind>/<run_id>/trace/ for unused_report
"""
from __future__ import annotations
from dataclasses import asdict, is_dataclass
from typing import Callable, Optional, Sequence, Any, Dict, Tuple
import io, cProfile, pstats, datetime, time
import numpy as np

from rune_decrypter_prime.core.config import (
    CipherConfig, ScoringConfig, RunConfig, SolverConfig, LoggingConfig
)
from rune_decrypter_prime.core.factory import build_solver
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.data.cipher_tests.baseline_registry import BASELINE
from rune_decrypter_prime.io.run_logger import get_logger


# ---------------- helpers ----------------
from pathlib import Path as _Path
import os as _os
try:
    from rune_decrypter_prime.core.config.logging_config import get_run_dir as _get_run_dir
except Exception:
    _get_run_dir = None
if not _os.environ.get('RDP_TEST_OUT_BASE'):
    _base = (_get_run_dir() / 'artifacts' / 'tests') if _get_run_dir else _Path('output') / 'tests' / 'manual' / 'artifacts' / 'tests'
    _base.mkdir(parents=True, exist_ok=True)
    _os.environ['RDP_TEST_OUT_BASE'] = str(_base)
def _coerce_dict(x: Any) -> Dict[str, Any]:
    if x is None:
        return {}
    if isinstance(x, dict):
        return x
    if is_dataclass(x):
        return asdict(x)
    if hasattr(x, "__dict__"):
        return dict(vars(x))
    return {}


def _preview_idx(idx: np.ndarray, n: int) -> str:
    n = max(0, int(n))
    head = idx[:n].tolist()
    return f"{head}… (len={idx.size})" if idx.size > n else f"{head}"


def _preview_rune(idx: np.ndarray, wli: Optional[np.ndarray], n: int) -> str:
    try:
        s = Runeglish.to_rune(idx, wli if wli is not None else None)
        return (s[:n] + "…") if len(s) > n else s
    except Exception:
        return "<runeglish-preview-error>"


# ---------------- harness ----------------
def run_roundtrip_case(
    *,
    cipher_name: str,
    plaintext_idx: np.ndarray,
    wli_data: Optional[Sequence[Sequence[int]]] = None,
    make_key: Callable[[np.random.Generator], np.ndarray],
    encrypt_fn: Callable[[np.ndarray, np.ndarray], np.ndarray],
    key_length: Optional[int],
    scorer_cfg_overrides: Optional[Dict[str, Any]] = None,
    optimizer_cfg_overrides: Optional[Dict[str, Any]] = None,
    preview: int = 48,
    verbose: bool = True,
    seed: Optional[int] = None,
    pt_ok_threshold: float = 1.0,
    device: Optional[str] = None,
    logging_cfg_overrides: Optional[Dict[str, Any]] = None,
    require_key_match: bool = True,
    use_test_key: bool = True,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Encrypt → config → solve → assert → debug print. Returns (known_key, found_key, sol.meta).
    If `require_key_match` is False, the helper does not force exact key equality; only the
    match-rate threshold (`pt_ok_threshold`) is enforced. This is useful for pure telemetry
    or shape contracts where solution correctness is irrelevant.
    """
    # ---------------- RNG + inputs ----------------
    seed = seed if seed is not None else BASELINE["seed"]
    rng = np.random.default_rng(seed)
    A = 29
    pt = np.asarray(plaintext_idx, dtype=np.uint8)
    wli = None
    if wli_data is not None:
        wli_arr = np.asarray(wli_data, dtype=np.uint8)
        if wli_arr.ndim == 1:
            wli_arr = np.stack([wli_arr, np.zeros_like(wli_arr)], axis=1)
        wli = wli_arr

    key = np.asarray(make_key(rng), dtype=np.uint8)
    ct = np.asarray(encrypt_fn(pt, key), dtype=np.uint8)

    # ---------------- configs ----------------
    c_cfg = CipherConfig(
        ciphertext=ct.tolist(),
        wli_data=(wli.tolist() if wli is not None else []),
        key_length=int(key_length) if key_length is not None else None,
        # todo add initial permutation
        #text_transposition="fwd",
        #key_transposition="fwd",
        name=cipher_name,
        device=device,
    )

    s_over = _coerce_dict(scorer_cfg_overrides)
    s_cfg = ScoringConfig(**{
        "include_char": True,
        "use_word_breaks": True,
        "n_char": 2, "n_wli": 2, "win": 10,
        "se_mode": "nose",
        "objective": "pct.logp.win10",
        "weights": (0.3, 0.7),
        "maximize": True,
        **s_over,
    })

    o_over = _coerce_dict(optimizer_cfg_overrides)
    use_test_key = bool(o_over.pop("use_test_key", use_test_key))
    # Make solver deterministic: propagate the test RNG seed to any optimizer API
    o_over.setdefault("seed", seed)

    opt_name = (o_over.get("name") or "beam").lower()
    base = {"name": opt_name, "verbose": False}
    if opt_name == "beam" and use_test_key:
        base.update({"beam_width": 1, "test_key": key.tolist()})
    elif opt_name == "hybrid" and use_test_key:
        # Let hybrid's initial beam stage take the same deterministic path
        base.update({"test_key": key.tolist()})
    o_cfg = SolverConfig.from_dict({**base, **o_over})

    # ---------------- logging ----------------
    log_over = _coerce_dict(logging_cfg_overrides)
    enable_trace = bool(log_over.pop("enable_trace", False))
    trace_sort = str(log_over.pop("trace_sort", "cumulative"))
    trace_top_n = int(log_over.pop("trace_top_n", 30))
    log_defaults = {"verbose": True, "print_progress": True, "write_jsonl": True}
    log_cfg = LoggingConfig(**{**log_defaults, **log_over})

    solver_cfg = RunConfig(
        cipher=c_cfg,
        scorer_name="rune",
        scorer_params=s_cfg,
        solver=o_cfg,
        logging=log_cfg,
        seed=seed
    )
    eng = build_solver(solver_cfg)

    # ---------------- unified logger ----------------
    log = get_logger()
    log.log_event({"type": "run_start",
                   "cipher": cipher_name,
                   "solver": o_cfg.name,
                   "device": device.value if device else None,
                   "seed": seed})

    # ---------------- solve (with optional trace) ----------------
    if enable_trace:
        print(f"[trace enabled] sort={trace_sort} top_n={trace_top_n}", flush=True)
        pr = cProfile.Profile()
        pr.enable()
        sol = eng.solve()
        pr.disable()
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats(trace_sort).print_stats(trace_top_n)
        trace_report = s.getvalue()
        log.log_trace({"func": f"{cipher_name}::{o_cfg.name}", "trace": trace_report})
    else:
        sol = eng.solve()
        trace_report = None

    found_key = np.asarray(sol.key, dtype=np.uint8)

    # ---------------- validation ----------------
    pt_known = eng.cipher.decrypt(ciphertext=ct, key=key)[0]
    pt_found = eng.cipher.decrypt(ciphertext=ct, key=found_key)[0]
    match_rate = float(np.mean(pt_found == pt_known))
    if match_rate < pt_ok_threshold:
        raise AssertionError(
            f"decryption below threshold match_rate={match_rate:.4f}, score={sol.score}"
        )


    if require_key_match and found_key.size == key.size and not np.array_equal(found_key, key):
        raise AssertionError(f"found key != known key\nfound={found_key.tolist()}\nknown={key.tolist()}")

    # ---------------- debug prints ----------------
    effective_verbose = bool(log_cfg.verbose) if logging_cfg_overrides is not None else bool(verbose)
    if effective_verbose:
        print("\n──────────────── debug ────────────────")
        print(f"cipher     : {cipher_name}")
        print(f"key (known): {key.tolist()}")
        print(f"key (found): {found_key.tolist()}")
        print(f"score      : {sol.score:.6f}")
        print(f"ct idx     : {_preview_idx(ct, preview)}")
        print(f"pt idx     : {_preview_idx(pt, preview)}")
        print(f"ct (rune)  : {_preview_rune(ct, wli, preview)}")
        print(f"pt (rune)  : {_preview_rune(pt, wli, preview)}")
        _tel = getattr(sol, "meta", {}).get("telemetry", {})
        encoding_dir_str = (
                _tel.get("encoding_dir")
                or _tel.get("scorer", {}).get("direction")
                or _tel.get("scorer", {}).get("dir")
                or _tel.get("scorer", {}).get("encoding_dir")
        )
        print(f"score encoding_dir : {encoding_dir_str}")
        if hasattr(sol, "plaintext") and sol.plaintext is not None:
            try:
                # If it's an array of rune indices, render to text for preview
                pt_sol_idx = np.asarray(sol.plaintext, dtype=np.uint8)
                print(f"pt(sol)    : {_preview_rune(pt_sol_idx, wli, preview)}")
            except Exception:
                # Otherwise assume it’s already a string
                print(f"pt(sol)    : {str(sol.plaintext)[:preview]}")
        if trace_report:
            print("──────── profile ({} top {}) ────────".format(trace_sort, trace_top_n))
            print(trace_report)
        print("───────────────────────────────────────\n")

    # ---------------- metadata augmentation ----------------
    # Add solve_time + acc into run_meta inside sol.meta
    t0 = time.perf_counter()
    _ = eng.solve()  # run again just to measure solve_time accurately
    solve_time = time.perf_counter() - t0

    pt_known = eng.cipher.decrypt(ciphertext=ct, key=key)[0]
    pt_found = eng.cipher.decrypt(ciphertext=ct, key=found_key)[0]
    acc = float(np.mean(pt_found == pt_known))

    run_meta = sol.meta.get("run_meta", {})
    run_meta.update({
        "solve_time": solve_time,
        "acc": acc,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    sol.meta["run_meta"] = run_meta

    if log_cfg.write_jsonl:
        log.log_event({"type": "run_meta", **run_meta})

    return key, found_key, sol.meta
