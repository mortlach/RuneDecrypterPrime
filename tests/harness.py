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
  - Uses rdp.io.run_logger.RunLogger
  - All events (start/end/errors/trace) go to JSONL in output/<kind>/<run_id>/logs/
  - Trace logs also go to output/<kind>/<run_id>/trace/ for unused_report
"""
from __future__ import annotations
from rdp import api
from dataclasses import asdict, is_dataclass
from typing import Callable, Optional, Sequence, Any, Dict, Tuple
import io
import cProfile
import pstats
import datetime
import time
import numpy as np
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.run import RunConfig
from rdp.core.config.solver import SolverConfig
from rdp.core.engine import EngineConfig, solve as engine_solve
from rdp.core.engine.finalization import finalize_solution
from rdp.core.problem.instance import ProblemInstance
from rdp.core.problem.spec import ProblemSpec
from rdp.core.types import KEY_DTYPE, ensure_direction
from rdp.data.runeglish import Runeglish
from tests._helpers.baseline_registry import BASELINE
from rdp.io.run_logger import get_logger
from pathlib import Path as _Path
try:
    from rdp.core.config.logging_config import get_run_dir as _get_run_dir
except Exception:
    _get_run_dir = None
_TEST_OUT_BASE = _get_run_dir() / 'artifacts' / 'tests' if _get_run_dir else _Path('output') / 'tests' / 'manual' / 'artifacts' / 'tests'
_TEST_OUT_BASE.mkdir(parents=True, exist_ok=True)

def _coerce_dict(x: Any) -> Dict[str, Any]:
    if x is None:
        return {}
    if isinstance(x, dict):
        return x
    if is_dataclass(x):
        return asdict(x)
    if hasattr(x, '__dict__'):
        return dict(vars(x))
    return {}

def _preview_idx(idx: np.ndarray, n: int) -> str:
    n = max(0, int(n))
    head = idx[:n].tolist()
    return f'{head}… (len={idx.size})' if idx.size > n else f'{head}'

def _preview_rune(idx: np.ndarray, wli: Optional[np.ndarray], n: int) -> str:
    try:
        s = Runeglish.to_rune(idx, wli if wli is not None else None)
        return s[:n] + '…' if len(s) > n else s
    except Exception:
        return '<runeglish-preview-error>'

def run_roundtrip_case(*, cipher_name: str, plaintext_idx: np.ndarray, wli_data: Optional[Sequence[Sequence[int]]]=None, make_key: Callable[[np.random.Generator], np.ndarray], encrypt_fn: Callable[[np.ndarray, np.ndarray], np.ndarray], key_length: Optional[int], scorer_cfg_overrides: Optional[Dict[str, Any]]=None, optimizer_cfg_overrides: Optional[Dict[str, Any]]=None, preview: int=48, verbose: bool=True, seed: Optional[int]=None, pt_ok_threshold: float=1.0, device: Optional[str]=None, logging_cfg_overrides: Optional[Dict[str, Any]]=None, require_key_match: bool=True, use_test_key: bool=True) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Encrypt → config → solve → assert → debug print. Returns (known_key, found_key, sol.meta).
    If `require_key_match` is False, the helper does not force exact key equality; only the
    match-rate threshold (`pt_ok_threshold`) is enforced. This is useful for pure telemetry
    or shape contracts where solution correctness is irrelevant.
    """
    seed = seed if seed is not None else BASELINE['seed']
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
    c_cfg = CipherConfig(ciphertext=ct.tolist(), wli_data=wli.tolist() if wli is not None else [], key_length=int(key_length) if key_length is not None else None, name=cipher_name, device=device)
    s_over = _coerce_dict(scorer_cfg_overrides)
    s_cfg = api.ScoringConfig.from_dict({**{'character_lane_enabled': True, 'word_length_lane_enabled': True, 'character_ngram_order': 2, 'word_length_ngram_order': 2, 'window_size': 10, 'objective': {'kind': 'percentile', 'statistic': 'log_probability', 'window_size': 10}, 'base_lane_weights': (0.3, 0.7), 'score_direction': 'maximize' if True else 'minimize', **s_over}})
    o_over = _coerce_dict(optimizer_cfg_overrides)
    use_test_key = bool(o_over.pop('use_test_key', use_test_key))
    o_over.setdefault('seed', seed)
    opt_name = (o_over.get('name') or 'beam').lower()
    base = {'name': opt_name, 'verbose': False}
    if opt_name == 'beam' and use_test_key:
        base.update({'beam_width': 1, 'test_key': key.tolist()})
    elif opt_name == 'hybrid' and use_test_key:
        base.update({'test_key': key.tolist()})
    o_cfg = SolverConfig.from_dict({**base, **o_over})
    log_over = _coerce_dict(logging_cfg_overrides)
    enable_trace = bool(log_over.pop("enable_trace", False))
    trace_sort = str(log_over.pop("trace_sort", "cumulative"))
    trace_top_n = int(log_over.pop("trace_top_n", 30))
    log_defaults = {
        "run_category": "tests",
        "label": "pytest",
        "verbose": True,
        "show_progress": True,
        "write_event_log": True,
    }
    log_cfg = api.LoggingConfig.from_dict({**{**log_defaults, **log_over}})
    solver_cfg = RunConfig(cipher=c_cfg, scorer_name='rune', scorer_params=s_cfg, solver=o_cfg, logging=log_cfg, seed=seed)
    direction = ensure_direction(c_cfg.encoding_dir)
    instance = ProblemInstance.materialise(
        ProblemSpec(
            text='',
            text_encoding_direction=direction,
            cipher_cfg=c_cfg,
            scorer_params=s_cfg,
            input_permutation=c_cfg.initial_text_permutation_indices,
        )
    )
    solver_params = dict(o_cfg.params)
    seed_keys = c_cfg.initial_keys
    engine_cfg = EngineConfig(
        solver=o_cfg.kind,
        params=solver_params,
        seed=solver_cfg.seed,
        stop_score=solver_params.get('stop_score'),
        verbose=bool(solver_params.get('verbose', True)),
        log_interval=int(solver_params.get('log_interval', 50)),
        seed_keys=(
            None
            if seed_keys is None or np.asarray(seed_keys).size == 0
            else np.asarray(seed_keys, dtype=KEY_DTYPE)
        ),
    )

    def solve_once():
        solution = engine_solve(instance, engine_cfg)
        return finalize_solution(
            instance.problem,
            solution,
            ciphertext=ct,
            wli=c_cfg.wli_data,
            cipher=c_cfg,
            encoding_dir=direction,
            cfg=solver_cfg,
            telemetry_on=solver_cfg.enable_telemetry,
            pipeline_block=instance.pipeline_block,
        )

    log = get_logger()
    log.log_event({'type': 'run_start', 'cipher': cipher_name, 'solver': o_cfg.name, 'device': device.value if device else None, 'seed': seed})
    if enable_trace:
        print(f'[trace enabled] sort={trace_sort} top_n={trace_top_n}', flush=True)
        pr = cProfile.Profile()
        pr.enable()
        sol = solve_once()
        pr.disable()
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats(trace_sort).print_stats(trace_top_n)
        trace_report = s.getvalue()
        log.log_trace({'func': f'{cipher_name}::{o_cfg.name}', 'trace': trace_report})
    else:
        sol = solve_once()
        trace_report = None
    found_key = np.asarray(sol.key, dtype=np.uint8)
    pt_known = instance.problem.cipher.decrypt(ciphertext=ct, key=key)[0]
    pt_found = instance.problem.cipher.decrypt(ciphertext=ct, key=found_key)[0]
    match_rate = float(np.mean(pt_found == pt_known))
    if match_rate < pt_ok_threshold:
        raise AssertionError(f'decryption below threshold match_rate={match_rate:.4f}, score={sol.score}')
    if require_key_match and found_key.size == key.size and (not np.array_equal(found_key, key)):
        raise AssertionError(f'found key != known key\nfound={found_key.tolist()}\nknown={key.tolist()}')
    effective_verbose = bool(log_cfg.verbose) if logging_cfg_overrides is not None else bool(verbose)
    if effective_verbose:
        print('\n──────────────── debug ────────────────')
        print(f'cipher     : {cipher_name}')
        print(f'key (known): {key.tolist()}')
        print(f'key (found): {found_key.tolist()}')
        print(f'score      : {sol.score:.6f}')
        print(f'ct idx     : {_preview_idx(ct, preview)}')
        print(f'pt idx     : {_preview_idx(pt, preview)}')
        print(f'ct (rune)  : {_preview_rune(ct, wli, preview)}')
        print(f'pt (rune)  : {_preview_rune(pt, wli, preview)}')
        _tel = getattr(sol, 'meta', {}).get('telemetry', {})
        encoding_dir_str = _tel.get('encoding_dir') or _tel.get('scorer', {}).get('direction') or _tel.get('scorer', {}).get('dir') or _tel.get('scorer', {}).get('encoding_dir')
        print(f'score encoding_dir : {encoding_dir_str}')
        if hasattr(sol, 'plaintext') and sol.plaintext is not None:
            try:
                pt_sol_idx = np.asarray(sol.plaintext, dtype=np.uint8)
                print(f'pt(sol)    : {_preview_rune(pt_sol_idx, wli, preview)}')
            except Exception:
                print(f'pt(sol)    : {str(sol.plaintext)[:preview]}')
        if trace_report:
            print('──────── profile ({} top {}) ────────'.format(trace_sort, trace_top_n))
            print(trace_report)
        print('───────────────────────────────────────\n')
    t0 = time.perf_counter()
    _ = solve_once()
    solve_time = time.perf_counter() - t0
    pt_known = instance.problem.cipher.decrypt(ciphertext=ct, key=key)[0]
    pt_found = instance.problem.cipher.decrypt(ciphertext=ct, key=found_key)[0]
    acc = float(np.mean(pt_found == pt_known))
    run_meta = sol.meta.get("run_meta", {})
    run_meta.update(
        {
            "solve_time": solve_time,
            "acc": acc,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
    )
    sol.meta["run_meta"] = run_meta
    if log_cfg.write_event_log:
        log.log_event({"type": "run_meta", **run_meta})
    return (key, found_key, sol.meta)
