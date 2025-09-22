# # ============================================================
# # rune_decrypter_prime/optimizers/hybrid_optimizer.py
# # Hybrid (Beam → GA → inline-SA polish), OptimizerXP-compatible
# # ============================================================
# ============================================================
# rune_decrypter_prime/optimizers/hybrid_optimizer.py
# Hybrid orchestrator: Beam → GA → SA
# ============================================================
from __future__ import annotations
import time
import numpy as np

from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
from rune_decrypter_prime.optimizers.ga_optimizer import GAOptimizer
from rune_decrypter_prime.optimizers.sa_optimizer import SAOptimizer
from rune_decrypter_prime.optimizers.beam_optimizer import BeamSearchOptimizer
from rune_decrypter_prime.core.config import OptimizerConfig, Solution
from rune_decrypter_prime.core.telemetry_helpers import (
    TelemetrySpan, attach_telemetry_to_meta
)
from rune_decrypter_prime.utils.runeglish import Runeglish


class HybridOptimizer(OptimizerBase):
    """
    Hybrid pipeline (pure orchestration):
      (optional) Beam warm start → GA exploration → SA polish

    No custom operators live here; we instantiate and call the real optimisers.

    Params (OptimizerConfig.params)
    --------------------------------
    use_beam: bool = True
    beam_width: int = 64
    beam_stop_score: Optional[float] = None

    # GA passthrough (same names as GAOptimizer)
    pop_size: int = 128
    generations: int = 150
    elite_frac: float = 0.05
    cx_frac: float = 0.8
    mut_prob: float = 0.25
    tournament_k: int = 3
    plateau_gens: int = 0

    # SA passthrough (same names as SAOptimizer)
    sa_init_temp: float = 0.5
    sa_min_temp: float = 1e-3
    sa_cooling: float = 0.998
    sa_auto_cooling: bool = True
    sa_iters: int = 2000

    # Common
    seed_keys: Optional[List[List[int]]] = None
    initial_keys: Optional[List[List[int]]] = None
    test_key: Optional[List[int]] = None
    stop_score: Optional[float] = None
    verbose: bool = False
    seed: Optional[int] = None
    """

    # Optional engine hooks (kept for API symmetry)
    def set_interrupt_idx(self, idx): pass
    def set_interrupt_search_space(self, pool, max_count): pass
    def set_transposition_modes(self, modes): pass

    def _decrypt_to_text(self, key_u8: np.ndarray) -> str:
        pt_idx = self.problem.cipher.decrypt(key=key_u8, ciphertext=self._ct)
        if isinstance(pt_idx, tuple):
            pt_idx = pt_idx[0]
        pt_idx = np.asarray(pt_idx, dtype=np.int64).ravel().tolist()
        return Runeglish.to_rune(pt_idx, self._wli)

    def search(self) -> Solution:
        # Fast path
        fast = self._maybe_return_test_key_fastpath("hybrid")
        if fast is not None:
            return fast

        seeds = [self.keyops.normalize(np.asarray(k, np.uint8))[:self.K] for k in self.seed_keys]
        params_for_span = {
            "use_beam": bool(self.get_param("use_beam", True)),
            "beam_width": int(self.get_param("beam_width", 64)),
            "K": int(self.K),
            "ga": {
                "pop": int(self.get_param("pop_size", 128)),
                "gens": int(self.get_param("generations", 150)),
                "elite_frac": float(self.get_param("elite_frac", 0.05)),
                "cx_frac": float(self.get_param("cx_frac", 0.8)),
                "mut_prob": float(self.get_param("mut_prob", 0.25)),
            },
            "sa": {
                "iters": int(self.get_param("sa_iters", 2000)),
                "T0": float(self.get_param("sa_init_temp", 0.5)),
                "Tmin": float(self.get_param("sa_min_temp", 1e-3)),
                "cool": float(self.get_param("sa_cooling", 0.998)),
            },
        }

        with TelemetrySpan(self.problem, "hybrid", params_for_span) as span:
            best_key = None
            best_score = -1e30

            # Stage 1: Beam (optional)
            use_beam = bool(self.get_param("use_beam", True))
            can_beam = bool(getattr(getattr(self.keyops, "caps", None), "can_partial_score", False))
            if use_beam and can_beam:
                if self.verbose:
                    print("[HYBRID] starting BEAM…")  # before Beam
                t0 = time.perf_counter()
                beam = BeamSearchOptimizer(problem=self.problem, opt_cfg=self.opt_cfg)
                sol_b = beam.search()
                dt = time.perf_counter() - t0
                bkey = np.asarray(sol_b.key, np.uint8)
                seeds.append(bkey)
                best_key = bkey.copy()
                best_score = float(sol_b.score)
                span.progress(stage="beam", elapsed_sec=float(dt), best=float(best_score))
                if self.verbose:
                    print(f"[HYBRID] BEAM done in {dt:.2f}s  best={best_score:.6f}")
                if self.stop_score is not None and best_score >= self.stop_score:
                    span.end(best_score=float(best_score))
                    meta = {"optimizer": "hybrid", "stage": "beam", "interrupt_idx": []}
                    meta = attach_telemetry_to_meta(self.problem, meta)
                    return Solution(best_key.tolist(), self._decrypt_to_text(best_key), best_score, meta)
            elif use_beam and not can_beam:
                # --- PSEUDO-BEAM (mono-friendly warm start) -------------------------
                # todo this is a "guess" based on assign chars to most common it really neds to exist in keyops to pmmlemtn partical scoring
                if self.verbose:
                    print("[HYBRID] TODO pseudo-beam: generating seeds (no partial scoring support) skipping")


            # Stage 2: GA (pass seeds via params to keep contracts)
            if self.verbose:
                print("[HYBRID] starting GA…")
            ga_params = dict(self.params)
            ga_params["initial_keys"] = [k.tolist() for k in seeds] if seeds else ga_params.get("initial_keys", [])
            if self.stop_score is not None:  # ← add this line
                ga_params["stop_score"] = float(self.stop_score)
            ga_cfg = OptimizerConfig(name="ga", params=ga_params)
            t0 = time.perf_counter()
            ga = GAOptimizer(problem=self.problem, opt_cfg=ga_cfg)
            sol_g = ga.search()
            dt = time.perf_counter() - t0
            gkey = np.asarray(sol_g.key, np.uint8)
            gscore = float(sol_g.score)
            if gscore > best_score:
                best_key, best_score = gkey.copy(), gscore
            span.progress(stage="ga", elapsed_sec=float(dt), best=float(best_score))
            if self.verbose:
                print(f"[HYBRID] GA done in {dt:.2f}s  best={best_score:.6f}")
            if self.stop_score is not None and best_score >= self.stop_score:
                span.end(best_score=float(best_score))
                meta = {"optimizer": "hybrid", "stage": "ga", "interrupt_idx": []}
                meta = attach_telemetry_to_meta(self.problem, meta)
                return Solution(best_key.tolist(), self._decrypt_to_text(best_key), best_score, meta)

            # Stage 3: SA polish (seeded with GA best)
            if self.verbose:
                print("[HYBRID] starting SA…")
            sa_params = dict(self.params)
            sa_params["initial_keys"] = [best_key.tolist()]
            if self.stop_score is not None:
                sa_params["stop_score"] = float(self.stop_score)
            sa_cfg = OptimizerConfig(name="sa", params=sa_params)
            t0 = time.perf_counter()
            sa = SAOptimizer(problem=self.problem, opt_cfg=sa_cfg)
            sol_s = sa.search()
            dt = time.perf_counter() - t0
            skey = np.asarray(sol_s.key, np.uint8)
            sscore = float(sol_s.score)
            if self.verbose:
                print(f"[HYBRID] SA done in {dt:.2f}s  best={best_score:.6f}")
            if sscore > best_score:
                best_key, best_score = skey.copy(), sscore
            span.progress(stage="sa", elapsed_sec=float(dt), best=float(best_score))

            span.end(best_score=float(best_score))

        pt_str = self._decrypt_to_text(best_key)
        meta = {"optimizer": "hybrid", "interrupt_idx": []}
        meta = attach_telemetry_to_meta(self.problem, meta)
        return Solution(best_key.tolist(), pt_str, float(best_score), meta)


# from __future__ import annotations
# from typing import List, Tuple
# import time
# import numpy as np
#
# from rune_decrypter_prime.utils.runeglish import Runeglish
# from rune_decrypter_prime.optimizers.beam_optimizer import BeamSearchOptimizer
# from rune_decrypter_prime.optimizers.ga_optimizer import GAOptimizer
# from rune_decrypter_prime.core.telemetry_helpers import (
#     TelemetrySpan, attach_telemetry_to_meta
# )
# from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
# from rune_decrypter_prime.core.config import Solution, OptimizerConfig
# from rune_decrypter_prime.core.problem import DecryptionProblem
# ArrayU8 = np.ndarray
#
#
# class HybridOptimizer(OptimizerBase):
#     """
#     Hybrid pipeline:
#       (optional) Beam warm start  →  GA exploration  →  tiny inline SA polish.
#
#     API (unchanged):
#       __init__(problem, cfg_cipher, **params)
#       set_interrupt_idx / set_interrupt_search_space / set_transposition_modes
#       search() -> Solution(key=list[uint8], plaintext=str, score=float, meta=dict)
#
#     XP-safe: heavy lifting goes through problem.evaluate_keys(...) and cipher.decrypt(...).
#
#     Params (OptimizerConfig.params):
#
#       # Beam
#       use_beam: bool = True
#       beam_width: int = 64
#       beam_stop_score: Optional[float] = None
#
#       # GA
#       pop_size: int = 128
#       generations: int = 150
#       elite_frac: float = 0.05
#       cx_frac: float = 0.7
#       mut_prob: float = 0.3
#       local_improve_iters: int = 200
#       local_improve_k: int = 1
#
#       # SA polish (inline)
#       sa_init_temp: float = 0.5
#       sa_min_temp: float = 1e-3
#       sa_cooling: float = 0.998
#       sa_iters: int = 2000
#       local_improve_iters_perm: int = 0   # per-step 2-swap micro-climb for perm keys
#
#       # Common
#       seed_keys: Optional[List[List[int]]] = None
#       test_key: Optional[List[int]] = None
#       stop_score: Optional[float] = None
#       verbose: bool = False
#       seed: Optional[int] = None          # RNG for SA polish only
#     """
#
#     # ------------------------ ctor ------------------------
#     def __init__(self, problem: DecryptionProblem, opt_cfg: OptimizerConfig):
#         super().__init__(problem, opt_cfg)
#
#         self.pop_size = self.get_param("pop_size", 128)
#
#         # verbosity & early stop
#         # Beam knobs
#         self.use_beam = bool(self.get_param("use_beam", True))
#         self.beam_width = int(self.get_param("beam_width", 64))
#         self.beam_stop = self.get_param("beam_stop_score", None)
#
#         # todo make holistic config: add GAConfig/SAConfig/BeamConfig as optional typed wrappers inside OptimizerConfig.params.
#         # GA knobs (forwarded to GAOptimizer)
#         self.ga_params = {
#         "pop_size" : self.get_param("pop_size", 128),
#         "generations" : self.get_param("generations", 50),
#         "elite_frac" : self.get_param("elite_frac", 0.05),
#         "cx_frac" : self.get_param("cx_frac", 0.70),
#         "mut_prob" : self.get_param("mut_prob", False),
#         "local_improve_iters" : self.get_param("local_improve_iters", 200),
#         "local_improve_k" : self.get_param("local_improve_k", 1),  # swaps per probe (perm),
#         "perm_batch_improve_size" : self.get_param("perm_batch_improve_size", 64),  # swaps per probe (perm),
#         "perm_batch_improve_rounds" : self.get_param("perm_batch_improve_rounds", 3),  # swaps per probe (perm),
#         }
#         # todo make holistic config: add GAConfig/SAConfig/BeamConfig as optional typed wrappers inside OptimizerConfig.params.
#         # SA (inline) knobs
#         self.sa_T0        = self.get_param("sa_init_temp", 0.5)
#         self.sa_Tmin      = self.get_param("sa_min_temp", 1e-3)
#         self.sa_cooling   = self.get_param("sa_cooling", 0.998)
#         self.sa_iters     = self.get_param("sa_iters", 2000)
#         self.sa_perm_improve     = self.get_param("sa_perm_improve", 0)
#
#         if self.verbose:
#             caps = getattr(self.keyops, "caps", None)
#             print(f"▶ Hybrid(use_beam={self.use_beam}) K={self.K} caps.kind={getattr(caps,'kind','?')}")
#
#         self._random = self.keyops.random
#         self._mutate = self.keyops.mutate
#         self._normalize = self.keyops.normalize
#         #
#         self._crossover = getattr(self.keyops, "crossover", None)  # optional
#
#     # ---------- Optional engine hooks (kept for symmetry with Beam/GA) ----------
#     def set_interrupt_idx(self, idx): pass
#     def set_interrupt_search_space(self, pool, max_count): pass
#     def set_transposition_modes(self, modes): pass
#
#     # ---------------- helpers ----------------
#     def _score_batch(self, keys_2d: np.ndarray) -> np.ndarray:
#         keys_2d = np.asarray(keys_2d, dtype=np.uint8, order="C")
#         return np.asarray(self.problem.evaluate_keys(keys_2d), dtype=np.float32)
#
#     def _score_key(self, k: np.ndarray) -> float:
#         return float(self._score_batch(k[None, :])[0])
#
#     def _decrypt_to_text(self, key_u8: np.ndarray) -> str:
#         pt_idx = self.problem.cipher.decrypt(key=key_u8, ciphertext=self._ct)[0]
#         return Runeglish.to_rune(pt_idx, self._wli)
#
#     # ---- tiny SA polish (inline, XP-safe) ----
#     def _sa_polish(self, start: np.ndarray) -> Tuple[np.ndarray, float]:
#         rng = np.random.default_rng(self.seed)
#         cur = self._normalize(start)[:self.K]
#         cur_s = self._score_key(cur)
#         best = cur.copy(); best_s = cur_s
#         T = self.sa_T0
#
#         def _perm_improve(k, s):
#             if getattr(self.keyops.caps, "kind", "") != "perm":
#                 return k, s
#             if self.sa_perm_improve <= 0:
#                 return k, s
#             cand = k.copy()
#             n = k.size
#             for _ in range(self.sa_perm_improve):
#                 i, j = rng.integers(0, n, size=2)
#                 if i == j:
#                     continue
#                 cand[:] = k
#                 cand[i], cand[j] = cand[j], cand[i]
#                 sc = self._score_key(cand)
#                 if sc > s:
#                     k, s = cand.copy(), sc
#             return k, s
#
#         it = 0
#         while it < self.sa_iters and T > self.sa_Tmin:
#             nbr = self._mutate(cur, rng)
#             nbr = self._normalize(nbr)[:self.K]
#             nbr_s = self._score_key(nbr)
#             d = nbr_s - cur_s
#             if d >= 0.0 or rng.random() < np.exp(d / max(1e-12, T)):
#                 cur, cur_s = nbr, nbr_s
#                 cur, cur_s = _perm_improve(cur, cur_s)
#
#             if cur_s > best_s:
#                 best, best_s = cur.copy(), float(cur_s)
#
#             if self.stop_score is not None and best_s >= self.stop_score:
#                 break
#
#             T = max(T * self.sa_cooling, self.sa_Tmin)
#             it += 1
#
#         best, best_s = _perm_improve(best, best_s)
#         return best, best_s
#
#     def search(self) -> Solution:
#         """
#         Run a hybrid optimizer: Beam → GA → SA polish.
#
#         Contract:
#           - Deterministic: seeded sub-optimizers; consistent across runs.
#           - Telemetry: wrapped in TelemetrySpan, records stage durations/scores.
#             span.end(best_score=...) is called BEFORE attaching telemetry, so
#             elapsed_sec & rollups are present.
#           - Device/scoring/dtype: delegated to sub-optimizers; no env/CLI reads.
#
#         Returns:
#           Solution(key: List[int], plaintext: str, score: float, meta: Dict[str, Any])
#         """
#         # --- Fast path for smoke tests ------------------------------------------
#         fast = self._maybe_return_test_key_fastpath("hybrid")
#         if fast is not None:
#             return fast
#         # --- Telemetry span setup ------------------------------------------------
#         params_for_span = {
#             "use_beam": bool(self.use_beam),
#             "beam_width": int(self.beam_width),
#             "ga": self.ga_params,
#             "sa": {
#                 "T0": self.sa_T0,
#                 "Tmin": self.sa_Tmin,
#                 "cool": self.sa_cooling,
#                 "iters": self.sa_iters,
#             },
#             "K": int(self.K),
#         }
#
#         seeds: List[np.ndarray] = [self._normalize(s)[: self.K] for s in self.seed_keys]
#         best_s = -1e9
#
#         # --- Staged optimization ------------------------------------------------
#         with TelemetrySpan(self.problem, "hybrid", params_for_span) as span:
#             # Stage 1: Beam
#             can_beam = bool(getattr(getattr(self.keyops, "caps", None), "can_partial_score", False))
#             if self.use_beam and can_beam:
#                 if self.verbose:
#                     print(f"[Hybrid] Stage 1: Beam (W={self.beam_width})")
#                 t_beam = time.perf_counter()
#                 beam = BeamSearchOptimizer(
#                     problem=self.problem,
#                     opt_cfg=self.opt_cfg
#                 )
#                 if hasattr(beam, "set_interrupt_idx"):
#                     beam.set_interrupt_idx(None)
#                 sol_b = beam.search()
#                 beam_key = np.asarray(sol_b.key, np.uint8)
#                 seeds.append(beam_key)
#                 dt_beam = time.perf_counter() - t_beam
#                 best_s = float(sol_b.score)
#                 span.progress(stage="beam", elapsed_sec=dt_beam, best=best_s)
#
#                 if self.stop_score is not None and best_s >= self.stop_score:
#                     span.end(best_score=float(best_s))
#                     meta = {"optimizer": "hybrid", "stage": "beam"}
#                     meta = attach_telemetry_to_meta(self.problem, meta)
#                     return Solution(beam_key.tolist(), sol_b.plaintext, float(best_s), meta)
#
#             # Stage 2: GA
#             if self.verbose:
#                 print("[Hybrid] Stage 2: GA")
#             ga = GAOptimizer(
#                 problem=self.problem,
#                 opt_cfg=self.opt_cfg
#             )
#             t_ga = time.perf_counter()
#             sol_g = ga.search()
#             best = np.asarray(sol_g.key, np.uint8)
#             best_s = float(sol_g.score)
#             dt_ga = time.perf_counter() - t_ga
#             span.progress(stage="ga", elapsed_sec=dt_ga, best=best_s)
#
#             if self.stop_score is not None and best_s >= self.stop_score:
#                 span.end(best_score=float(best_s))
#                 # todo interrupt_idx ??
#                 meta = {"optimizer": "hybrid", "stage": "ga", "interrupt_idx": []}
#                 meta = attach_telemetry_to_meta(self.problem, meta)
#                 return Solution(best.tolist(), self._decrypt_to_text(best), best_s, meta)
#
#             # Stage 3: SA polish
#             if self.verbose:
#                 print("[Hybrid] Stage 3: SA polish")
#             t_sa = time.perf_counter()
#             best2, best2_s = self._sa_polish(best)
#             if best2_s > best_s:
#                 best, best_s = best2, best2_s
#             dt_sa = time.perf_counter() - t_sa
#             span.progress(stage="sa", elapsed_sec=dt_sa, best=float(best_s))
#
#             # finalize span BEFORE telemetry capture
#             span.end(best_score=float(best_s))
#
#         # --- Final decrypt & telemetry attach -----------------------------------
#         pt_str = self._decrypt_to_text(best)
#         meta = {"optimizer": "hybrid", "interrupt_idx": []}
#         meta = attach_telemetry_to_meta(self.problem, meta)
#
#         return Solution(best.tolist(), pt_str, best_s, meta)
