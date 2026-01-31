# ============================================================
# rune_decrypter_prime/solver/base.py
# ============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Union
from contextlib import AbstractContextManager
import time
import numpy as np

# Core enums / guards
from ..core.types import (
    Device,
    Direction,
    SolverName,
    ObjectiveFamily,
    ensure_device,
    ensure_direction,
    ensure_solver_name,
    KEY_DTYPE,
)

# Utils
from ..utils.runeglish import Runeglish  # for plaintext rendering

# Telemetry
from ..telemetry.events import (
    solver_start as opt_start,
    solver_progress as opt_progress,
    solver_end as opt_end,
    attach_telemetry_to_meta,
)
from ..telemetry.pipeline import make_pipeline_block

# Solution + logging
from ..core.config import Solution
from ..io.logging_adapter import module_logger

logger = module_logger(__name__)


def _to_plaintext_str(pt_u8, wli):
    try:
        return Runeglish.to_rune(pt_u8, wli)
    except Exception:
        return ""


class TelemetrySpan(AbstractContextManager):
    """Context wrapper emitting start/progress/end via telemetry utils."""
    def __init__(self, problem, name: str, params: Dict[str, Any] | None = None):
        self.problem = problem
        self.name = str(name)
        self.params = dict(params or {})
        self._t0: Optional[float] = None
        self.ended: bool = False

    def __enter__(self):
        self._t0 = time.perf_counter()
        opt_start(self.problem, self.name, self.params)
        return self

    def progress(self, **step):
        opt_progress(self.problem, self.name, **step)

    def end(self, **result):
        if not self.ended and self._t0 is not None:
            opt_end(self.problem, self.name, result, self._t0)
            self.ended = True

    def __exit__(self, exc_type, exc, tb):
        if not self.ended and self._t0 is not None:
            if exc:
                self.end(error=str(exc))
            else:
                self.end()
        return False


@dataclass
class OptimizerMeta:
    name: str
    params: dict
    seed: Optional[int] = None


def _unwrap_params_dict(p):
    """Accept {'params': {...}} or flat dict and return a flat dict."""
    if isinstance(p, dict) and isinstance(p.get("params"), dict):
        q = dict(p)
        inner = q.pop("params")
        q.update(inner)  # inner wins
        return q
    return p if isinstance(p, dict) else {}


class SolverBase:
    """
    Shared base for all solvers.

    Contract (unchanged):
      - Attributes: problem, keyops, K, seed_keys, stop_score, verbose, log_interval, rng
      - Methods   : get_param, _score_batch/_evaluate_keys, _decrypt_to_text,
                    _maybe_return_test_key_fastpath, _make_solution

    New (generic) early-stop:
      - Plateau across steps (rounds/generations/iters), with a min_delta improvement threshold.
      - Works for all solvers by calling `_update_best_and_check_patience(best, step)`.
    """

    # ---- Telemetry whitelists ----
    _SPAN_WHITELIST_PARAMS = {
        # GA
        "pop_size", "generations", "elite_frac", "cx_frac", "mut_prob", "tournament_k",
        "perm_batch_improve_rounds", "perm_batch_improve_size",
        # SA
        "iters", "T0", "Tmin", "cool", "accept_in_log", "log_eps", "local_improve_on_accept",
        # Beam / Hybrid
        "beam_width", "use_beam", "rounds",
        # Kaeding
        "steps", "restarts", "inner_batch", "block_schedule",
        "slip_every", "slip_blocks", "col_every", "col_batch",
        # Early stop (generic)
        "stop_score", "plateau_rounds", "plateau_min_delta",
        # common
        "K", "seed", "verbose", "log_interval", "progress_pct", "print_progress", "verbose_console",
        "progress_preview_chars",
        "seed_keys_count", "seed_source",
    }
    _PROGRESS_WHITELIST = {
        "step", "gen", "generation", "iter", "depth", "pct",
        "attempted", "evaluated", "kept", "pruned",
        "improved", "accepted", "rejected",
        "top", "best", "best_score", "temp",
        "decrypt_time_s", "score_time_s", "tokens",
        "phase", "reason", "round", "rounds", "parents", "cands_per_parent",
        "evals",
        "block", "restart", "slip", "col_moves",
        "hamming_weight",
        # plateau
        "since_improve", "patience_left",
        # sa stuff
        "accepts", "accept_rate",
    }

    def __init__(
        self,
        problem: Any,
        *,
        optimizer_name: str,
        params: dict,
        rng: np.random.Generator,
        seed_keys: Optional[Sequence[np.ndarray]] = None,
        stop_score: Optional[float] = None,
        verbose: bool = True,
        log_interval: int = 50,
    ):
        self.problem = problem
        self.keyops = getattr(problem, "keyops")
        self.key_dtype = getattr(self.keyops, "dtype", KEY_DTYPE)
        self.K: int = int(self.keyops.caps.length)
        self.solver_name: SolverName = ensure_solver_name(optimizer_name)
        self.optimizer_name = self.solver_name.value
        raw_params = _unwrap_params_dict(params or {})
        self.params = dict(raw_params)  # flat & canonical if UI did its job
        self.rng = rng
        self.seed_keys = seed_keys
        self.stop_score = stop_score
        self.verbose = bool(verbose)
        self.log_interval = int(log_interval)
        self.verbose_console = bool(
            self.params.get("verbose_console", self.params.get("print_progress", False))
        )
        self.params.setdefault("verbose_console", self.verbose_console)

        c_cfg = getattr(problem, "c_cfg", None)
        try:
            dev_raw = getattr(c_cfg, "device", Device.CPU) if c_cfg is not None else Device.CPU
            self.device: Device = ensure_device(dev_raw)
        except Exception:
            self.device = Device.CPU
        try:
            dir_raw = getattr(c_cfg, "encoding_dir", Direction.LTR) if c_cfg is not None else Direction.LTR
            self.encoding_direction: Direction = ensure_direction(dir_raw)
        except Exception:
            self.encoding_direction = Direction.LTR

        # Percent-based progress (prints every X% when verbose)
        self.progress_pct: int = int(self.params.get("progress_pct", 1))
        self._next_pct_mark: int = self.progress_pct  # next threshold to print
        self.progress_preview_chars: int = max(
            0, int(self.params.get("progress_preview_chars", 0) or 0)
        )
        self.params.setdefault("progress_preview_chars", self.progress_preview_chars)

        # Early stop / plateau (generic)
        self.plateau_rounds: int = int(self.params.get("plateau_rounds", 0))
        self.plateau_min_delta: float = float(self.params.get("plateau_min_delta", 0.0))
        self._best_score_so_far: float = -np.inf
        self._best_at_step: int = 0
        self._last_best = float("-inf")
        self._last_improve_step = 0

        # Accumulators (fallback; Problem counters are source of truth)
        self._tokens_processed = 0
        self._decrypt_time = 0.0
        self._score_time = 0.0
        self._candidates_evaluated = 0
        self._seed_diag: Dict[str, Any] = {}

        # Normalize seed_keys (strict: no silent fallback)
        if self.seed_keys is not None and len(self.seed_keys) > 0:
            arr = np.asarray(self.seed_keys, dtype=self.key_dtype)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            normalized_rows = []
            for i, row in enumerate(arr):
                try:
                    norm = np.asarray(self.keyops.normalize(row), dtype=self.key_dtype)
                except Exception as exc:
                    raise ValueError(f"Invalid seed key at index {i}") from exc
                if norm.ndim == 2:
                    norm = norm[0]
                if norm.shape[0] != self.K:
                    raise ValueError(f"Seed key at index {i} has length {norm.shape[0]}, expected {self.K}")
                normalized_rows.append(norm)
            self.seed_keys = np.ascontiguousarray(np.vstack(normalized_rows), dtype=self.key_dtype)

    # ---------------- Param + telemetry helpers ----------------

    def get_param(self, name: str, default: Any = None) -> Any:
        d = self.params or {}
        if isinstance(d, dict) and "params" in d and isinstance(d["params"], dict):
            # wrapper form: {'name':'sa','params':{...}}
            return d["params"].get(name, d.get(name, default))
        return d.get(name, default)

    def _to_plain(self, v: Any) -> Any:
        try:
            import numpy as _np
            if isinstance(v, _np.generic):
                return v.item()
            if isinstance(v, _np.ndarray):
                if v.size == 1:
                    return v.reshape(()).item()
                return int(v.size)
        except Exception:
            pass
        if isinstance(v, (int, float, str, bool)) or v is None:
            return v
        return str(v)

    def _public_params(self) -> Dict[str, Any]:
        out = {}
        for k, v in (self.params or {}).items():
            if k in self._SPAN_WHITELIST_PARAMS and v is not None:
                out[k] = self._to_plain(v)
        out.setdefault("K", self.K)
        # include stop_score/plateau from kwargs if not in params
        if "stop_score" not in out and self.stop_score is not None:
            out["stop_score"] = self._to_plain(self.stop_score)
        if "plateau_rounds" not in out and self.plateau_rounds:
            out["plateau_rounds"] = self.plateau_rounds
        if "plateau_min_delta" not in out and self.plateau_min_delta:
            out["plateau_min_delta"] = self.plateau_min_delta
        # seed introspection (uniform)
        try:
            n_seeds = 0
            if getattr(self, "seed_keys", None) is not None:
                sk = self.seed_keys
                n_seeds = int(getattr(sk, "shape", (0,))[0]) if hasattr(sk, "shape") else (len(sk) if hasattr(sk, "__len__") else 1)
            out.setdefault("seed_keys_count", n_seeds)
            out.setdefault("seed_source", "provided" if n_seeds > 0 else "none")
        except Exception:
            pass
        return out

    def _start_span(self) -> TelemetrySpan:
        span = TelemetrySpan(self.problem, name=self.optimizer_name, params=self._public_params())
        span.__enter__()  # explicit enter so we can keep a handle
        self._span = span
        return span

    def _progress(self, **kwargs):
        """
        Emit a progress event to TelemetrySpan (always), with payload filtered by the whitelist.
        Console printing is handled by the caller (GA/SA/Beam) and should not be gated here.
        """
        if not getattr(self, "_span", None):
            return
        data = {k: self._to_plain(v) for k, v in kwargs.items() if k in self._PROGRESS_WHITELIST}
        if data:
            self._span.progress(**data)

    def _live_counters(self) -> Dict[str, Any]:
        """
        Read live counters for tokens and timings.
        Priority:
          1) Problem.telemetry  (authoritative in the current design)
          2) Problem.telemetry_counters (legacy dict, if someone populates it)
          3) Internal accumulators maintained by SolverBase (fallback)
        """
        tele = getattr(self.problem, "telemetry", None)
        if tele is not None:
            return {
                "tokens": int(getattr(tele, "tokens_processed", 0) or 0),
                "decrypt_time_s": float(getattr(tele, "decrypt_time_s", 0.0) or 0.0),
                "score_time_s": float(getattr(tele, "score_time_s", 0.0) or 0.0),
                "evals": int(getattr(tele, "candidates_evaluated", 0) or 0),
            }

        pt = getattr(self.problem, "telemetry_counters", None)
        if isinstance(pt, dict):
            return {
                "tokens": int(pt.get("tokens_processed", 0) or 0),
                "decrypt_time_s": float(pt.get("decrypt_time_s", 0.0) or 0.0),
                "score_time_s": float(pt.get("score_time_s", 0.0) or 0.0),
                "evals": int(pt.get("candidates_evaluated", 0) or 0),
            }

        logger.info("solver base: falling back to internal counters")
        return {
            "tokens": int(getattr(self, "_tokens_processed", 0) or 0),
            "decrypt_time_s": float(getattr(self, "_decrypt_time", 0.0) or 0.0),
            "score_time_s": float(getattr(self, "_score_time", 0.0) or 0.0),
            "evals": int(getattr(self, "_candidates_evaluated", 0) or 0),
        }

    def _progress_pct(self, current_step: int, total_steps: int, **fields):
        """
        Percent-bucketed progress emitter. Call this freely from solver;
        throttling is handled here. Includes live counters (tokens/decrypt/score)
        from Problem.telemetry (preferred), with safe fallbacks.
        """
        if total_steps <= 0 or self.progress_pct <= 0:
            return

        pct = int((100 * current_step) // max(1, total_steps))
        fired = False
        while self._next_pct_mark <= 100 and pct >= self._next_pct_mark:
            self._next_pct_mark += self.progress_pct
            fired = True
        if not fired:
            return

        live = self._live_counters()
        payload = dict(fields)
        preview_key = payload.pop("preview_key", None)
        payload.setdefault("step", int(current_step))
        payload.update({
            "pct": pct,
            "decrypt_time_s": live["decrypt_time_s"],
            "score_time_s": live["score_time_s"],
            "tokens": live["tokens"],
        })
        hw = getattr(self, "_hamming_weight_current", None)
        if hw is not None:
            payload.setdefault("hamming_weight", hw)
        if live.get("evals") is not None:
            payload.setdefault("evals", live["evals"])

        if getattr(self, "plateau_rounds", 0) > 0:
            try:
                since = int(self._since_improve(current_step))
            except Exception:
                since = int(payload.get("since_improve", 0))
            payload.setdefault("since_improve", since)
            payload.setdefault("patience_left", max(0, int(self.plateau_rounds) - since))

        extra_fields = {}
        extra_fn = getattr(self, "extra_progress_fields", None)
        if callable(extra_fn):
            try:
                extra_fields = extra_fn() or {}
            except Exception:
                extra_fields = {}
        for k, v in (extra_fields or {}).items():
            payload.setdefault(k, v)

        if self.progress_preview_chars > 0 and not payload.get("preview"):
            preview = self._plaintext_preview(preview_key, self.progress_preview_chars)
            if preview:
                payload.setdefault("preview", preview)

        self._maybe_console_progress(payload)
        self._run_progress_callback(payload, preview_key)
        self._progress(**payload)

    def _run_progress_callback(self, payload, preview_key):
        tele = getattr(self.problem, "telemetry", None)
        cb = None
        if tele is not None:
            try:
                cb = getattr(tele, "progress_callback", None)
            except Exception:
                cb = None
            if cb is None and isinstance(tele, dict):
                cb = tele.get("progress_callback")
        if not callable(cb):
            return
        key_list = None
        if preview_key is not None:
            key_arr = np.asarray(preview_key, dtype=self.key_dtype).reshape(-1)
            key_list = key_arr.astype(int).tolist()
        cb(dict(payload), key_list)

    # ---------------- Early-stop / Patience helpers ----------------
    def _maybe_console_progress(self, payload: Dict[str, Any]) -> None:
        """Emit a short console line if verbose_console is enabled."""
        if not (self.verbose and self.verbose_console):
            return
        pct = payload.get("pct")
        try:
            pct_val = int(pct)
        except Exception:
            pct_val = None
        best = payload.get("best_score", payload.get("best"))
        best_str = ""
        if best is not None:
            try:
                best_str = f" best={float(best):.6f}"
            except Exception:
                best_str = f" best={best}"
        best_raw = payload.get("best_raw")
        if best_raw is not None:
            try:
                best_str += f" raw={float(best_raw):.6f}"
            except Exception:
                best_str += f" raw={best_raw}"
        evals = payload.get("evals")
        evals_str = f" evals={int(evals)}" if isinstance(evals, (int, float)) else ""
        since = payload.get("since_improve")
        since_str = f" since={int(since)}" if isinstance(since, (int, float)) else ""
        reason = payload.get("reason")
        reason_str = f" reason={reason}" if reason else ""
        preview = payload.get("preview")
        preview_str = ""
        if preview:
            snippet = str(preview).replace("\n", " ")
            preview_str = f' text="{snippet}"'
        prefix = f"[{self.optimizer_name} {pct_val:3d}%]" if pct_val is not None else f"[{self.optimizer_name}]"
        print(f"{prefix}{best_str}{evals_str}{since_str}{reason_str}{preview_str}", flush=False)

    def _since_improve(self, step: int) -> int:
        """Steps since the last qualifying improvement."""
        return int(step) - int(getattr(self, "_best_at_step", 0) or 0)

    def _register_step_best(self, current_best: float, step: int) -> bool:
        """Update the running best. Returns True if we improved by ≥ plateau_min_delta."""
        improved = False
        if current_best > (self._best_score_so_far + self.plateau_min_delta):
            self._best_score_so_far = float(current_best)
            self._best_at_step = int(step)
            improved = True
        return improved

    def _patience_should_stop(self, step: int) -> bool:
        """True if plateau is active and we've gone 'plateau_rounds' steps with no improvement."""
        if self.plateau_rounds <= 0:
            return False
        return self._since_improve(step) >= self.plateau_rounds

    def _update_best_and_check_patience(self, current_best: float, step: int) -> bool:
        """Convenience: register improvement and return early-stop decision."""
        self._register_step_best(current_best, step)
        return self._patience_should_stop(step)

    # ---------------- Scoring adapters ----------------

    def _evaluate_keys(self, keys: np.ndarray) -> np.ndarray:
        """Single source for scoring; enforces shapes/dtypes and accumulates telemetry."""
        if keys.dtype != self.key_dtype:
            keys = keys.astype(self.key_dtype, copy=False)
        if keys.ndim == 1:
            keys = keys.reshape(1, -1)
        assert keys.shape[1] == self.K, f"Key length mismatch: {keys.shape[1]} != {self.K}"

        eval_fn = getattr(self.problem, "evaluate_keys", None) or \
                  getattr(self.problem, "_evaluate_keys", None) or \
                  self._slow_evaluate_keys

        t0 = time.perf_counter()
        scores = eval_fn(keys)
        t1 = time.perf_counter()

        if isinstance(scores, tuple) and len(scores) == 3:
            scores, dec_t, sc_t = scores
            self._decrypt_time += float(dec_t)
            self._score_time += float(sc_t)
        else:
            self._score_time += (t1 - t0)

        # Token accounting: prefer problem counters if defined; else estimate
        ct_len = int(getattr(self.problem, "ciphertext_len", 0) or getattr(self.problem, "N_tokens", 0) or 0)
        if ct_len:
            self._tokens_processed += int(keys.shape[0]) * ct_len

        self._candidates_evaluated += int(keys.shape[0])
        return np.asarray(scores, dtype=np.float64)

    # ---------------- Hamming annealing helper ----------------
    def _maybe_update_hamming_progress(self, progress: float) -> None:
        """
        If the scorer exposes set_hamming_progress, update it with a progress fraction [0,1].
        Stores the current weight (best-effort) for diagnostics.
        """
        scorer = getattr(self.problem, "scorer", None)
        fn = getattr(scorer, "set_hamming_progress", None) if scorer is not None else None
        if callable(fn):
            try:
                fn(progress)
                self._hamming_weight_current = getattr(scorer, "_hamming_weight", None)
            except Exception:
                self._hamming_weight_current = None

    def _slow_evaluate_keys(self, keys: np.ndarray) -> np.ndarray:
        """Extremely conservative fallback."""
        scores = np.empty((keys.shape[0],), dtype=np.float64)
        decrypt = getattr(self.problem, "decrypt_to_text", None)
        scorer = getattr(self.problem, "score_plaintext", None)
        for i, k in enumerate(keys):
            if decrypt:
                pt = decrypt(k)
            else:
                resolve = getattr(self.problem, "resolve_plaintext", None)
                if callable(resolve):
                    pt = resolve(k)
                    if pt is None:
                        pt = self.problem.cipher.decrypt(self.problem.ciphertext, k)
                else:
                    pt = self.problem.cipher.decrypt(self.problem.ciphertext, k)
            scores[i] = float(scorer(pt)) if scorer else float(self.problem.scorer.score(pt))
        return scores

    def _pipeline_snapshot(self) -> Optional[dict]:
        """Build a canonical pipeline telemetry block if data is available."""
        problem = getattr(self, "problem", None)
        if problem is None:
            return None

        direction = getattr(self, "encoding_direction", Direction.LTR)
        c_cfg = None
        try:
            c_cfg = getattr(problem, "c_cfg", None)
            if c_cfg is not None:
                dir_candidate = getattr(c_cfg, "encoding_dir", None)
                if dir_candidate is not None:
                    direction = ensure_direction(dir_candidate)
        except Exception:
            pass

        perm = None
        cipher = getattr(problem, "cipher", None)
        if cipher is not None:
            perm = getattr(cipher, "initial_text_permutation_indices", None)
        if perm is None and c_cfg is not None:
            perm = getattr(c_cfg, "initial_text_permutation_indices", None)
        if perm is None:
            pipeline = getattr(problem, "pipeline", None)
            if pipeline is not None:
                ip = getattr(pipeline, "input_permutation", None)
                if isinstance(ip, dict):
                    perm = ip.get("indices") or ip.get("perm")
                elif ip is not None and hasattr(ip, "__iter__"):
                    perm = list(ip)

        perm_iter = None
        if perm is not None:
            try:
                perm_iter = [int(p) for p in perm]
            except Exception:
                try:
                    perm_iter = list(perm)
                except Exception:
                    perm_iter = None

        ct_len = getattr(problem, "ciphertext_len", None)
        if ct_len is None:
            ct = getattr(problem, "ciphertext", None)
            try:
                ct_len = int(len(ct))
            except Exception:
                ct_len = 0
        try:
            length = int(ct_len or 0)
        except Exception:
            length = 0

        try:
            return make_pipeline_block(
                text_encoding_direction=direction,
                ciphertext_len=max(0, length),
                text_permutation=perm_iter,
            )
        except Exception:
            return None

    def _interruptor_meta(self, key: np.ndarray) -> Optional[Dict[str, Any]]:
        """Best-effort interruptor metadata for pretty printers."""
        problem = getattr(self, "problem", None)
        if problem is None:
            return None
        c_cfg = getattr(problem, "c_cfg", None)
        if c_cfg is None:
            return None

        mode = None
        expected = None
        cfg = getattr(c_cfg, "interruptors_cfg", None)
        if cfg is not None and hasattr(cfg, "mode"):
            mode = getattr(cfg, "mode", None)
            if mode == "exact":
                expected = list(getattr(cfg, "exact", None) or [])
        else:
            exact = getattr(c_cfg, "interruptors_exact", None)
            legacy = getattr(c_cfg, "interruptors", None)
            if exact is not None or legacy is not None:
                mode = "exact"
                expected = list(exact or legacy or [])

        split = getattr(self.keyops, "split_key", None)
        if not callable(split):
            return None
        try:
            core, intr = split(key)
            core_len = int(np.asarray(core, dtype=self.key_dtype).reshape(-1).size)
            intr_vals = np.asarray(intr, dtype=np.int64).reshape(-1)
            found = [int(v) for v in intr_vals.tolist() if int(v) >= 0]
        except Exception:
            return None

        meta: Dict[str, Any] = {"found": found}
        if mode is not None:
            meta["mode"] = mode
        if expected is not None:
            meta["expected"] = list(expected)
        if core_len >= 0:
            meta["core_length"] = core_len
        return meta

    # ---------------- Finalization ----------------

    def _make_solution(self, best_key: np.ndarray, best_score: float) -> Solution:
        return self._finalize_solution(best_key, best_score)

    def _finalize_solution(self, best_key: np.ndarray, best_score: float) -> Solution:
        k = np.ascontiguousarray(best_key, dtype=self.key_dtype).reshape(-1)
        try:
            budget = max(4096, int(self.K) * 64) if hasattr(self, "K") else 4096
            base_hints = self._local_improve_hints()
            for _ in range(10):
                hint_payload = dict(base_hints)
                hint_payload["budget"] = budget
                k2, s2 = self._local_improve(k, float(best_score), self.rng, **hint_payload)
                if s2 <= best_score + 1e-9:
                    break
                k, best_score = k2, s2
                budget = max(128, budget // 2)
        except Exception:
            pass
        resolve = getattr(self.problem, "resolve_plaintext", None)
        pt = resolve(k) if callable(resolve) else None
        if pt is None:
            pt = self.problem.cipher.decrypt(ciphertext=self.problem.ciphertext, key=k)
        pt_u8 = np.asarray(pt, dtype=np.uint8)
        if pt_u8.ndim >= 2:
            pt_u8 = pt_u8[0]
        pt_u8 = pt_u8.reshape(-1)

        sol = Solution(key=k.copy(), plaintext=pt_u8.copy(), score=float(best_score))
        try:
            sol.plaintext_idx = pt_u8.tolist()
        except Exception:
            pass
        try:
            sol.plaintext_str = _to_plaintext_str(pt_u8, getattr(self.problem, "wli_data", None))
        except Exception:
            pass

        try:
            if not hasattr(sol, "meta") or sol.meta is None:
                sol.meta = {}
            sol.meta.setdefault("solver", self.solver_name.value)
            live = self._live_counters()
            work = sol.meta.setdefault("work", {})
            timings = sol.meta.setdefault("timings", {})
            if isinstance(live, dict):
                if live.get("tokens") is not None:
                    work.setdefault("tokens", int(live["tokens"]))
                if live.get("evals") is not None:
                    work.setdefault("evals", int(live["evals"]))
                if live.get("decrypt_time_s") is not None:
                    work.setdefault("decrypt_time_s", float(live["decrypt_time_s"]))
                    timings.setdefault("decrypt_time_s", float(live["decrypt_time_s"]))
                if live.get("score_time_s") is not None:
                    work.setdefault("score_time_s", float(live["score_time_s"]))
                    timings.setdefault("score_time_s", float(live["score_time_s"]))
        except Exception:
            pass

        try:
            intr_meta = self._interruptor_meta(k)
            if intr_meta:
                sol.meta.setdefault("interruptors", intr_meta)
        except Exception:
            pass

        try:
            if getattr(self, "_seed_diag", None):
                seed_meta = sol.meta.setdefault("seed_diag", {})
                if isinstance(seed_meta, dict):
                    seed_meta.update(self._seed_diag)
        except Exception:
            pass

        # Attach solver events + UI blocks
        attach_telemetry_to_meta(sol, self.problem)
        return sol

    def _plaintext_preview(self, key, max_chars: int) -> str:
        """Decrypt ``key`` and return a short plaintext preview (best-effort)."""
        if key is None or max_chars <= 0:
            return ""
        try:
            cipher = getattr(self.problem, "cipher", None)
            ciphertext = getattr(self.problem, "ciphertext", None)
            if cipher is None or ciphertext is None:
                return ""
            k = np.asarray(key, dtype=self.key_dtype).reshape(-1)
            resolve = getattr(self.problem, "resolve_plaintext", None)
            pt = resolve(k) if callable(resolve) else None
            if pt is None:
                pt = cipher.decrypt(ciphertext=ciphertext, key=k)
            pt_u8 = np.asarray(pt, dtype=np.uint8)
            if pt_u8.ndim >= 2:
                pt_u8 = pt_u8[0]
            pt_u8 = pt_u8.reshape(-1)
            wli = getattr(self.problem, "wli_data", None)
            preview = ""
            try:
                preview = Runeglish.to_rune_latin(pt_u8.tolist(), wli if wli is not None else None)
            except Exception:
                preview = _to_plaintext_str(pt_u8, wli)
            if not preview:
                preview = "".join(str(int(v)) for v in pt_u8[:max_chars])
            preview = preview.replace("\n", " ").strip()
            return preview[:max_chars]
        except Exception:
            return ""

    # ---------------- Span end with richer fallbacks ----------------

    def _end_span(self, span: Optional[TelemetrySpan] = None, **result):
        if span is None:
            span = getattr(self, "_span", None)
        if not span:
            return

        payload = {k: self._to_plain(v) for k, v in (result or {}).items()}
        reason = payload.get("reason")
        if reason:
            self._stop_reason = str(reason)
        elif payload.get("error") and not getattr(self, "_stop_reason", None):
            self._stop_reason = "error"
        elif not getattr(self, "_stop_reason", None):
            self._stop_reason = "done"

        # Preferred: explicit counters
        pt = getattr(self.problem, "telemetry_counters", None)
        if isinstance(pt, dict):
            payload.setdefault("tokens", self._to_plain(pt.get("tokens_processed")))
            dt = pt.get("decrypt_time_s", pt.get("decrypt_time"))
            if dt is not None:
                payload.setdefault("decrypt_time_s", self._to_plain(dt))
            st = pt.get("score_time_s", pt.get("score_time"))
            if st is not None:
                payload.setdefault("score_time_s", self._to_plain(st))
            ce = pt.get("candidates_evaluated")
            if ce is not None:
                payload.setdefault("evals", self._to_plain(ce))

        # Problem.telemetry object/dict fallbacks
        tel = getattr(self.problem, "telemetry", None)
        if (payload.get("decrypt_time_s") in (None, 0, 0.0)) and tel is not None:
            for k in ("decrypt_time_s", "dec_time", "time_dec"):
                v = getattr(tel, k, None) if not isinstance(tel, dict) else tel.get(k)
                if v is not None:
                    payload["decrypt_time_s"] = self._to_plain(v); break
        if (payload.get("score_time_s") in (None, 0, 0.0)) and tel is not None:
            for k in ("score_time_s", "sc_time", "time_score"):
                v = getattr(tel, k, None) if not isinstance(tel, dict) else tel.get(k)
                if v is not None:
                    payload["score_time_s"] = self._to_plain(v); break
        if payload.get("tokens") in (None, 0, 0.0) and tel is not None:
            for k in ("tokens_processed", "tokens"):
                v = getattr(tel, k, None) if not isinstance(tel, dict) else tel.get(k)
                if v is not None:
                    payload["tokens"] = self._to_plain(v); break
        if payload.get("evals") in (None, 0, 0.0) and tel is not None:
            for k in ("candidates_evaluated", "evals"):
                v = getattr(tel, k, None) if not isinstance(tel, dict) else tel.get(k)
                if v is not None:
                    payload["evals"] = self._to_plain(v); break

        # Final fallback: internal accumulators
        payload.setdefault("tokens",         self._tokens_processed)
        payload.setdefault("decrypt_time_s", self._decrypt_time)
        payload.setdefault("score_time_s",   self._score_time)
        payload.setdefault("evals",          getattr(self, "_candidates_evaluated", 0))

        pipeline_block = self._pipeline_snapshot()
        if pipeline_block is not None:
            payload.setdefault("pipeline", pipeline_block)

        span.end(**payload)
        self._span = None

    # ---------------- Early-stop controls (public helpers) ----------------

    def _early_stop_reset(self, initial_best: float, plateau_override: int | None = None) -> None:
        """Initialise early-stop state; keeps public/internal mirrors in sync."""
        pr = int(self.get_param("plateau_rounds", 0) or 0)
        self._plateau_rounds = int(plateau_override if plateau_override is not None else pr) or 0
        self.plateau_rounds = self._plateau_rounds

        pd = float(self.get_param("plateau_min_delta", 0.0) or 0.0)
        self._plateau_delta = pd
        self.plateau_min_delta = pd

        self._best_score_so_far = float(initial_best)
        self._last_improve_at = 0
        self._best_at_step = 0
        self._stop_reason = None

    def _early_stop_update(self, current_best: float, step: int) -> bool:
        """Update plateau state; return True if plateau triggers a stop."""
        min_delta = float(getattr(self, "_plateau_delta",
                                  getattr(self, "plateau_min_delta", 0.0)) or 0.0)
        if (current_best - self._best_score_so_far) > min_delta:
            self._best_score_so_far = float(current_best)
            self._last_improve_at = int(step)
            self._best_at_step = int(step)
            return False
        if int(getattr(self, "plateau_rounds", 0) or 0) <= 0:
            return False
        if (int(step) - int(self._last_improve_at)) >= int(self.plateau_rounds):
            self._stop_reason = f"no_improve_{int(self.plateau_rounds)}"
            return True
        return False

    def _early_stop_stop_score(self, current_best: float) -> bool:
        """Stop immediately if a target score is configured and reached."""
        target = self.get_param("stop_score", None)
        if target is None:
            return False
        try:
            target = float(target)
        except Exception:
            return False
        if float(current_best) >= target:
            self._stop_reason = "target_score"
            return True
        return False

    # ---------------- Core scoring entrypoint ----------------

    def _score_batch(self, pop: np.ndarray) -> np.ndarray:
        """Canonical batch evaluation via Problem (decrypt+score+WLI)."""
        scores = self.problem.evaluate_keys(pop)
        return self._rank_scores(scores)

    def _objective_family(self):
        obj = getattr(getattr(self.problem, "scorer", None), "objective", None)
        return getattr(obj, "family", None)

    def _rank_scores(self, scores: np.ndarray) -> np.ndarray:
        fam = self._objective_family()
        if fam is ObjectiveFamily.NEGLOGP:
            return -np.asarray(scores, dtype=np.float64)
        return scores

    # ---------------- Seed diagnostics ----------------

    def _append_seed_diag(self, tag: str, payload: Dict[str, Any]) -> None:
        try:
            if not isinstance(self._seed_diag, dict):
                self._seed_diag = {}
            self._seed_diag[tag] = payload
        except Exception:
            pass

    def _capture_seed_quality(self) -> None:
        if self.seed_keys is None:
            return
        try:
            count = len(self.seed_keys)
        except Exception:
            count = 0
        if count == 0:
            return
        if isinstance(self._seed_diag, dict) and "baseline" in self._seed_diag:
            return
        try:
            seeds = np.asarray(self.seed_keys, dtype=self.key_dtype)
            if seeds.ndim == 1:
                seeds = seeds.reshape(1, -1)
            seeds = np.ascontiguousarray(seeds[:, : self.K], dtype=self.key_dtype)
            if seeds.shape[1] != self.K:
                return
            seed_scores = self._score_batch(seeds)
            if "make_population" in getattr(self.keyops.caps, "ops", set()):
                random = self.keyops.make_population(seeds.shape[0], self.rng)
            else:
                random = np.vstack([self.keyops.random(self.rng) for _ in range(seeds.shape[0])]).astype(
                    self.key_dtype
                )
            random_scores = self._score_batch(random)
            payload = {
                "count": int(seeds.shape[0]),
                "seed_score_mean": float(np.mean(seed_scores)),
                "seed_score_max": float(np.max(seed_scores)),
                "random_score_mean": float(np.mean(random_scores)),
                "random_score_max": float(np.max(random_scores)),
            }
            self._append_seed_diag("baseline", payload)
        except Exception as exc:
            self._append_seed_diag("baseline_error", {"error": str(exc)})

    # ---------------- Utilities used by solvers ----------------

    def _maybe_return_test_key_fastpath(self, tag: Union[SolverName, str, None] = None):
        """
        If a test key is supplied, score and return it (skip search). Debug/smoke only.
        """
        tk = getattr(self.problem.c_cfg, "test_key", None)
        if tk is None:
            tk = self.params.get("test_key", None)
            if tk is None:
                return None

        key_arr = np.asarray(tk, dtype=self.key_dtype)
        key_arr = self.keyops.normalize(key_arr)[: self.K]
        if key_arr.ndim != 1 or key_arr.shape[0] != self.K:
            key_arr = key_arr.reshape(-1)[: self.K].astype(self.key_dtype, copy=False)

        resolve = getattr(self.problem, "resolve_plaintext", None)
        pt_idx = resolve(key_arr) if callable(resolve) else None
        if pt_idx is None:
            pt_idx = self.problem.cipher.decrypt(key=key_arr, ciphertext=self.problem.ciphertext)
        if isinstance(pt_idx, tuple):
            pt_idx = pt_idx[0]
        pt_idx = np.asarray(pt_idx, dtype=np.int64)
        if pt_idx.ndim >= 2:
            pt_idx = pt_idx[0]
        pt_idx = pt_idx.ravel()
        pt_list = pt_idx.tolist()

        wli = getattr(self.problem, "wli_data", None)
        if wli is None:
            wli = getattr(getattr(self.problem, "c_cfg", None), "wli_data", None)
        pt_str = Runeglish.to_rune(pt_list, wli)
        score = float(self._score_batch(key_arr[None, :])[0])

        solver_tag = tag.value if isinstance(tag, SolverName) else tag
        solver_str = solver_tag or getattr(self, "optimizer_name", self.solver_name.value)
        sol = Solution(key_arr.tolist(), pt_str, score, {"solver": solver_str, "reason": "test_key"})
        meta = getattr(sol, "meta", {})
        if isinstance(meta, dict):
            work = meta.setdefault("work", {})
            work.setdefault("evals", 1)
            work.setdefault("decrypt_time_s", 0.0)
            work.setdefault("score_time_s", 0.0)
            meta.setdefault("timings", {})
            sol.meta = meta
        attach_telemetry_to_meta(sol, self.problem)
        self._stop_reason = "test_key"
        meta = getattr(sol, "meta", None)
        if not isinstance(meta, dict):
            meta = {}
            sol.meta = meta
        tel = meta.setdefault("telemetry", {})
        tel.setdefault("device", getattr(getattr(self.problem, "device", None), "value", "cpu"))
        tel.setdefault("dtype", "float32")
        tel.setdefault(
            "tokens_processed",
            int(getattr(getattr(self.problem, "telemetry", {}), "tokens_processed", 0) or 0),
        )
        progress = tel.setdefault("solver_progress", [])
        progress.append({
            "solver": solver_str,
            "step": 0,
            "pct": 100,
            "best_score": score,
            "evals": 1,
            "reason": "test_key",
        })
        run = tel.setdefault("run", {})
        now = time.time()
        run.setdefault("solver", solver_str)
        run.setdefault("device", tel.get("device", "cpu"))
        run.setdefault("start_ts", now)
        run.setdefault("end_ts", now)
        run.setdefault("result", {"score": score, "reason": "test_key"})
        return sol

    def _decrypt_to_text(self, key_u8: np.ndarray) -> str:
        resolve = getattr(self.problem, "resolve_plaintext", None)
        pt_idx = resolve(key_u8) if callable(resolve) else None
        if pt_idx is None:
            pt_idx = self.problem.cipher.decrypt(key=key_u8, ciphertext=self._ct)
        if isinstance(pt_idx, tuple):
            pt_idx = pt_idx[0]
        pt_idx = np.asarray(pt_idx, dtype=np.int64)
        if pt_idx.ndim >= 2:
            pt_idx = pt_idx[0]
        pt_idx = pt_idx.ravel().tolist()
        return Runeglish.to_rune(pt_idx, wli=getattr(self.problem.c_cfg, "wli_data", None))

    def _local_improve(self, key: np.ndarray, score: float, rng, **hint):
        """
        Generic local improver driven by KeyOps verbs+hints.
        If keyops exposes 'local_improve', delegate; else no-op.
        """
        keyops = self.keyops
        local_improve = getattr(keyops, "local_improve", None)
        if not callable(local_improve):
            return key, float(score)

        key = np.ascontiguousarray(key, dtype=self.key_dtype)

        def _score_fn_any(x):
            x = np.asarray(x, dtype=self.key_dtype)
            if x.ndim == 1:
                return float(self._score_batch(x[None, :])[0])
            return self._score_batch(x)

        default_hints = getattr(keyops, "hints", None) or {}
        merged_hint = dict(default_hints)
        merged_hint.update(hint or {})

        k2, s2 = local_improve(
            key=key, score=float(score), scorer=_score_fn_any, rng=rng, hint=merged_hint,
        )
        k2 = np.ascontiguousarray(k2, dtype=self.key_dtype)
        return k2, float(s2)

    def _keyops_family(self) -> str:
        caps = getattr(self.keyops, "caps", None)
        if caps is None:
            return ""
        traits = getattr(caps, "traits", {}) or {}
        family = traits.get("family")
        if family is None:
            family = getattr(caps, "kind", None)
        if hasattr(family, "value"):
            family = family.value
        return str(family or "").lower()

    def _local_improve_hints(self) -> Dict[str, Any]:
        """
        Derive solver-aware hints for keyops.local_improve so we can mirror
        the Stage-1 permutation polish without hard-coding inside solvers.
        """
        hints: Dict[str, Any] = {}
        if self._keyops_family() == "permutation":
            params = self.params or {}
            hints["perm_batch_size"] = int(params.get("perm_batch_improve_size", 64))
            hints["perm_batch_rounds"] = int(params.get("perm_batch_improve_rounds", 3))
            hints["perm_hill_iters"] = int(params.get("perm_hill_iters",
                                                      params.get("local_improve_iters", 200)))
            hints["perm_hill_swaps"] = int(params.get("perm_hill_swaps",
                                                      params.get("local_improve_k", 2)))
        return hints

    def _maybe_early_stop(
        self,
        *,
        best_score: float | None,
        current_step: int | None,
        total_steps: int | None,
        stop_score: float | None = None,
        plateau_rounds: int | None = None,
        since_improve: int | None = None,
        progress_fields: dict | None = None,
    ) -> tuple[bool, str]:
        """
        Unified early-stop checks for all solvers.
        Emits a progress tick with a 'reason' when a stop condition hits.
        """
        reason = ""

        if (stop_score is not None) and (best_score is not None) and (best_score >= float(stop_score)):
            reason = "stop_score"
        elif plateau_rounds and (since_improve is not None) and (since_improve >= int(plateau_rounds)):
            reason = f"no_improve_{int(plateau_rounds)}"

        if reason:
            fields = dict(progress_fields or {})
            fields.update({"reason": reason})
            if reason.startswith("no_improve_"):
                fields["plateau"] = True
            self._progress_pct(
                current_step=current_step,
                total_steps=total_steps,
                best_score=best_score,
                **fields,
            )
            return True, reason

        return False, ""

    def _maybe_best_of_seeds(self, rng):
        """
        Return the best key from provided seeds (seed_keys or initial_key),
        or fall back to a random key.
        """
        seed_keys = getattr(self, "seed_keys", None)
        initial_key = getattr(self, "initial_key", None)

        no_seeds = False
        if seed_keys is None:
            no_seeds = True
        elif isinstance(seed_keys, np.ndarray):
            no_seeds = (seed_keys.size == 0)
        elif isinstance(seed_keys, (list, tuple)):
            no_seeds = (len(seed_keys) == 0)

        if no_seeds:
            if initial_key is not None:
                key = np.ascontiguousarray(np.array(initial_key, dtype=self.key_dtype))
                if key.ndim == 2:
                    key = key[0]
                elif key.ndim != 1:
                    key = self.keyops.normalize(key)
                    if key.ndim == 2:
                        key = key[0]
                return key.astype(self.key_dtype, copy=False)
            return self.keyops.random(rng).astype(self.key_dtype, copy=False)

        seeds = np.array(seed_keys, dtype=self.key_dtype, copy=False)
        if seeds.ndim == 1:
            seeds = seeds[None, :]
        seeds = np.ascontiguousarray(seeds, dtype=self.key_dtype)

        if seeds.shape[1] != self.K:
            rows = []
            for row in seeds:
                fixed = self.keyops.normalize(row)
                if fixed.ndim == 2:
                    fixed = fixed[0]
                rows.append(np.ascontiguousarray(fixed, dtype=self.key_dtype))
            seeds = np.ascontiguousarray(np.stack(rows, axis=0), dtype=self.key_dtype)

        scores = self._score_batch(seeds)
        # If subclass overrides _score_batch, ensure objective direction is enforced here.
        if type(self)._score_batch is not SolverBase._score_batch:
            scores = self._rank_scores(scores)
        best_idx = int(np.argmax(scores))
        return seeds[best_idx].copy()

    # Optional family-specific helper (retained)
    def _local_improve_add(self, key: np.ndarray, score: float) -> tuple[np.ndarray, float]:
        """Greedy sweep for additive keys (column-wise maximise)."""
        kind = getattr(self.keyops.caps, "kind", "") or getattr(self.keyops.caps, "traits", {}).get("family", "")
        if kind != "additive":
            return key, float(score)
        k = self.keyops.normalize(key).copy()
        best = float(score)
        A, K = int(self.A), int(k.size)
        for col in range(K):
            batch = np.tile(k, (A, 1)).astype(self.key_dtype)
            batch[:, col] = np.arange(A, dtype=self.key_dtype)
            scores = self._score_batch(batch)
            j = int(np.argmax(scores))
            if scores[j] > best:
                k[col] = self.key_dtype.type(j)
                best = float(scores[j])
        return k, best
