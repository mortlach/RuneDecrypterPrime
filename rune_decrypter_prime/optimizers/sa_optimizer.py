# ============================================================
# rune_decrypter_prime/optimizers/sa_optimizer.py
#   Simulated Annealing (device-agnostic, KeyOps-driven)
# ============================================================
from __future__ import annotations
import math
import numpy as np

from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
from rune_decrypter_prime.core.config import OptimizerConfig, Solution
from rune_decrypter_prime.core.telemetry_helpers import (
    TelemetrySpan, attach_telemetry_to_meta
)


class SAOptimizer(OptimizerBase):
    """
    Simulated Annealing over the cipher key space via cipher.keyops.

    Params (OptimizerConfig.params)
    --------------------------------
    sa_init_temp: float = 1.0
    sa_min_temp : float = 1e-3
    sa_cooling  : float = 0.995          # if sa_auto_cooling=False, used directly
    sa_auto_cooling: bool = True         # if True, set cooling so T(iters)=Tmin
    sa_iters    : int   = 10000
    patience    : int   = 0              # 0 disables plateau early-stop
    tol         : float = 1e-6           # min improvement to count as “better”
    local_improve_on_accept: bool = True
    sa_elitism  : bool = True
    sa_reseed_interval: int = 5000
    sa_rescue_drop_abs: float = 0.02
    sa_rescue_drop_ratio: float = 0.5

    Common:
    seed, initial_keys, test_key, stop_score, verbose, log_interval
    """

    def __init__(self, problem, opt_cfg: OptimizerConfig):
        super().__init__(problem, opt_cfg)

        # Annealing controls
        # self.T0 = float(self.get_param("sa_init_temp", 1.0))
        # self.Tmin = float(self.get_param("sa_min_temp", 1e-3))
        # self.cooling = float(self.get_param("sa_cooling", 0.995))
        # self.auto_cooling = bool(self.get_param("sa_auto_cooling", True))
        # self.iters = int(self.get_param("sa_iters", 10_000))
        # self.patience = int(self.get_param("patience", 0))
        # self.tol = float(self.get_param("tol", 1e-6))

        # Annealing controls (accept both 'sa_*' and plain names)
        self.T0 = float(
            self.get_param("sa_init_temp",
                           self.get_param("T0", 1.0))
        )
        self.Tmin = float(
            self.get_param("sa_min_temp",
                           self.get_param("Tmin", 1e-3))
        )
        self.cooling = float(
            self.get_param("sa_cooling",
                           self.get_param("cooling", 0.995))
        )
        self.auto_cooling = bool(
            self.get_param("sa_auto_cooling",
                           self.get_param("auto_cooling", True))
        )
        self.iters = int(
            self.get_param("sa_iters",
                           self.get_param("iters", 10_000))
        )

        self.patience = int(self.get_param("patience", 0))
        self.tol = float(self.get_param("tol", 1e-6))

        # Local polish
        self.local_improve_on_accept = bool(
            self.get_param("local_improve_on_accept", True)
        )

        # Elitism / safety ropes (accept both 'sa_*' and plain names)
        self.elitism = bool(
            self.get_param("sa_elitism",
                           self.get_param("elitism", True))
        )
        self.reseed_interval = int(
            self.get_param("sa_reseed_interval",
                           self.get_param("reseed_interval", 5000))
        )
        self.rescue_drop_abs = float(
            self.get_param("sa_rescue_drop_abs",
                           self.get_param("rescue_drop_abs", 0.02))
        )
        self.rescue_drop_ratio = float(
            self.get_param("sa_rescue_drop_ratio",
                           self.get_param("rescue_drop_ratio", 0.5))
        )

        # If auto-cooling, derive geometric factor so T_end ≈ Tmin
        if self.auto_cooling and self.T0 > 0 and self.Tmin > 0 and self.iters > 0:
            self.cooling = float((self.Tmin / self.T0) ** (1.0 / float(self.iters)))



    # ---- energy on log-scale for robust acceptance ----
    @staticmethod
    def _energy(score: float) -> float:
        eps = 1e-12
        return -math.log(max(score, eps))

    def _select_mutator(self):
        """Choose the richest available neighbour function."""
        if getattr(self.keyops.caps, "kind", "") != "perm":
            return self.keyops.mutate
        # prefer mixed neighbourhoods when available
        if hasattr(self.keyops, "mutate_mixed"):
            return self.keyops.mutate_mixed
        return self.keyops.mutate

    def search(self) -> Solution:
        rng = self.rng

        fast = self._maybe_return_test_key_fastpath("sa")
        if fast is not None:
            return fast

        mutator = self._select_mutator()
        if self.verbose:
            print(f"[SA] keyops={self.keyops.caps.kind}/{self.keyops.caps.length}, "
                  f"mutator={getattr(mutator, '__name__', 'fn')}")

        params_for_span = {
            "iters": int(self.iters),
            "T0": float(self.T0),
            "Tmin": float(self.Tmin),
            "cooling": float(self.cooling),
            "K": int(self.K),
        }

        # 5% progress step across annealing iterations
        pct_step = max(1, self.iters // 20)
        accepts, sweeps = 0, 0
        last_improve_it = 0

        with TelemetrySpan(self.problem, "sa", params_for_span) as span:
            # Seed & quick polish
            key = self._maybe_best_of_seeds(rng).astype(np.uint8)
            score = self._score_key(key)
            best_key, best_score = key.copy(), float(score)
            best_key, best_score = self._local_improve_perm(best_key, best_score, rng, rounds=2, batch_pairs=256)
            best_key, best_score = self._local_improve_add(best_key, best_score)
            key, score = best_key.copy(), float(best_score)

            if self.verbose:
                print(f"[SA-init] score={score:.6f}")

            T = float(self.T0)
            for it in range(self.iters):
                cand = mutator(key, rng).astype(np.uint8)
                if np.all(cand == key):
                    cand = self.keyops.mutate(key, rng).astype(np.uint8)

                cand_score = self._score_key(cand)
                d_score = cand_score - score
                accept = (d_score >= 0.0) or (rng.random() < math.exp(d_score / max(T, 1e-12)))

                if accept:
                    accepts += 1
                    key, score = cand, cand_score
                    if score > best_score + self.tol:
                        sweeps += 1
                        if self.local_improve_on_accept:
                            key, score = self._local_improve_perm(key, score, rng, rounds=1, batch_pairs=128)
                            key, score = self._local_improve_add(key, score)
                        best_key, best_score = key.copy(), float(score)
                        last_improve_it = it

                # Elitism / rescue
                if self.elitism:
                    if self.reseed_interval > 0 and ((it + 1) % self.reseed_interval == 0):
                        key, score = best_key.copy(), float(best_score)
                    if (score < best_score - self.rescue_drop_abs) or (score < best_score * self.rescue_drop_ratio):
                        key, score = best_key.copy(), float(best_score)

                # Stop rules
                if self.stop_score is not None and best_score >= self.stop_score:
                    if self.verbose:
                        print(f"[SA-stop] reached stop_score={self.stop_score}")
                    break
                if self.patience > 0 and (it - last_improve_it) >= self.patience:
                    if self.verbose:
                        print(f"[SA-stop] no improvement in {self.patience} iterations")
                    break

                # Cool
                T = max(T * self.cooling, self.Tmin)

                # Telemetry & kid-friendly progress printing
                should_log = (
                    (self.log_interval and it % self.log_interval == 0)
                    or (it % pct_step == 0)
                    or (it == self.iters - 1)
                )
                if should_log:
                    pct = 100.0 * (it + 1) / max(1, self.iters)
                    acc_rate = float(accepts / max(1, it + 1))
                    if self.verbose:
                        print(f"[SA {pct:5.1f}%] it={it:6d}  T={T:.5f}  curr={score:.6f}  best={best_score:.6f}  acc={acc_rate:.3f}")
                    span.progress(
                        it=int(it), T=float(T),
                        score=float(score), best=float(best_score),
                        accepts_so_far=int(accepts), sweeps_so_far=int(sweeps),
                        accept_rate=acc_rate,
                    )

            span.end(best_score=float(best_score))

        pt_str = self._decrypt_to_text(best_key)
        meta = {"optimizer": "sa", "interrupt_idx": []}
        meta = attach_telemetry_to_meta(self.problem, meta)
        return Solution(best_key.tolist(), pt_str, float(best_score), meta)


# # todo we are tetsign this one!!
#
# # ============================================================
# # rune_decrypter_prime/optimizers/sa_optimizer.py
# #   Simulated Annealing (device-agnostic, KeyOps-driven)
# # ============================================================
# from __future__ import annotations
# from typing import Optional
# import numpy as np
# import math
#
#
# from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
# from rune_decrypter_prime.core.config import OptimizerConfig, Solution
# from rune_decrypter_prime.core.problem import DecryptionProblem
# from rune_decrypter_prime.utils.runeglish import Runeglish
# from rune_decrypter_prime.core.telemetry_helpers import (
#     TelemetrySpan, attach_telemetry_to_meta
# )
#
# ArrayU8 = np.ndarray
#
#
# class SAOptimizer(OptimizerBase):
#     """
#     Simulated Annealing over the cipher's key space via cipher.keyops.
#
#     Params (OptimizerConfig.params):
#       sa_init_temp: float = 1.0
#       sa_min_temp : float = 1e-3
#       sa_cooling  : float = 0.995
#       sa_auto_cooling: bool = True
#       sa_iters    : int   = 10000
#       stop_score  : float|None = None
#       verbose     : bool  = False
#
#       # Permutation mutator knobs
#       perm_mutate_mix   : tuple|None
#       perm_block_size   : int|None
#       perm_rotate_size  : int|None
#       local_improve_on_accept: bool = True
#     """
#
#     def __init__(self, problem: DecryptionProblem, opt_cfg: OptimizerConfig):
#         super().__init__(problem, opt_cfg)
#
#         self.stop_score = self.get_param("stop_score", None)  # float
#         self.patience = int(self.get_param("patience", 0))  # 0 = disabled
#         self.tol = float(self.get_param("tol", 1e-6))  # min improvement
#
#         # Annealing params
#         self.T0           = float(self.get_param("sa_init_temp", 1.0))
#         self.Tmin         = float(self.get_param("sa_min_temp", 1e-3))
#         self.cooling      = float(self.get_param("sa_cooling", 0.995))
#         self.auto_cooling = bool(self.get_param("sa_auto_cooling", True))
#         self.iters        = int(self.get_param("sa_iters", 10_000))
#         self.stop_score   = self.get_param("stop_score", None)
#         # Seed keys from SolveSpec (defaults to [])
#         self.seed_keys = opt_cfg.params.get("initial_keys", []) or []
#         print(f"[SA] using {len(self.seed_keys)} initial seeds")
#         # Mutation neighbourhood controls
#         self._perm_mutate_mix   = self.get_param("perm_mutate_mix", None)
#         self._perm_block_size   = self.get_param("perm_block_size", None)
#         self._perm_rotate_size  = self.get_param("perm_rotate_size", None)
#         self.local_improve_on_accept = bool(self.get_param("local_improve_on_accept", True))
#
#         self.elitism = bool(self.get_param("sa_elitism", True))
#         self.reseed_interval = int(self.get_param("sa_reseed_interval", 5000))
#         self.rescue_drop_abs = float(self.get_param("sa_rescue_drop_abs", 0.02))
#         self.rescue_drop_ratio = float(self.get_param("sa_rescue_drop_ratio", 0.5))
#
#         # If auto_cooling requested, set cooling so T_end = Tmin at iters
#         if self.auto_cooling and self.T0 > 0 and self.Tmin > 0 and self.iters > 0:
#             self.cooling = float((self.Tmin / self.T0) ** (1.0 / float(self.iters)))
#
#     def _energy(self, score: float) -> float:
#         eps = 1e-12
#         return -math.log(max(score, eps))
#
#
#     # ---------------- helpers -----------------------------------
#     @staticmethod
#     def _as_numpy(x) -> np.ndarray:
#         try:
#             if hasattr(x, "detach") and hasattr(x, "cpu") and hasattr(x, "numpy"):
#                 return x.detach().cpu().numpy()
#             if hasattr(x, "get"):
#                 import numpy as _np
#                 return _np.asarray(x.get())
#         except Exception:
#             pass
#         import numpy as _np
#         return _np.asarray(x)
#
#     def _score_key(self, key_u8: np.ndarray) -> float:
#         out = self.problem.evaluate_keys(key_u8[None, :])
#         arr = self._as_numpy(out)
#         return float(arr[0])
#
#     def _score_batch(self, keys_2d: np.ndarray) -> np.ndarray:
#         out = self.problem.evaluate_keys(keys_2d)
#         return self._as_numpy(out)
#
#     def _decrypt_to_text(self, key_u8: np.ndarray) -> str:
#         pt_idx = self.problem.cipher.decrypt(key=key_u8, ciphertext=self._ct)
#         if isinstance(pt_idx, tuple):  # decrypt may return (pt, meta)
#             pt_idx = pt_idx[0]
#         pt_idx = np.asarray(pt_idx, dtype=np.int64).ravel().tolist()
#         return Runeglish.to_rune(pt_idx, self._wli)
#
#     def _maybe_best_of_seeds(self, rng: np.random.Generator) -> np.ndarray:
#         if not self.seed_keys:
#             return self.keyops.random(rng).astype(np.uint8)
#         keys = [self.keyops.normalize(np.asarray(k, np.uint8)) for k in self.seed_keys]
#         uniq, seen = [], set()
#         for k in keys:
#             t = tuple(int(x) for x in k)
#             if t not in seen:
#                 seen.add(t); uniq.append(k)
#         batch = np.stack(uniq, axis=0).astype(np.uint8)
#         scores = self._score_batch(batch)
#         j = int(np.argmax(scores))
#         return batch[j].copy()
#
#     def _local_improve_add(self, key: np.ndarray, score: float) -> tuple[np.ndarray, float]:
#         if getattr(self.keyops.caps, "kind", "") != "additive":
#             return key, float(score)
#         k = self.keyops.normalize(key).copy()
#         best = float(score)
#         A = getattr(self.problem.cipher, "A", 29)
#         K = k.size
#         for col in range(K):
#             batch = np.tile(k, (A, 1)).astype(np.uint8)
#             batch[:, col] = np.arange(A, dtype=np.uint8)
#             scores = self._score_batch(batch)
#             j = int(np.argmax(scores))
#             if scores[j] > best:
#                 k[col] = np.uint8(j); best = float(scores[j])
#         return k, best
#
#     def _local_improve_perm(self, key: np.ndarray, score: float,
#                             rng: np.random.Generator,
#                             rounds: int = 3, batch_pairs: int = 256) -> tuple[np.ndarray, float]:
#         if getattr(self.keyops.caps, "kind", "") != "perm":
#             return key, float(score)
#         k = self.keyops.normalize(key).astype(np.uint8).copy()
#         best = float(score)
#         has_batch = hasattr(self.keyops, "batch_2swap_candidates")
#         K = int(k.size)
#         for _ in range(max(1, rounds)):
#             pairs = np.column_stack([rng.integers(0, K, size=batch_pairs),
#                                      rng.integers(0, K, size=batch_pairs)]).astype(np.int64)
#             if has_batch:
#                 cand = self.keyops.batch_2swap_candidates(k, pairs)
#             else:
#                 M = int(batch_pairs)
#                 cand = np.tile(k[None, :], (M, 1))
#                 for m in range(M):
#                     i, j = int(pairs[m,0]), int(pairs[m,1])
#                     if i != j:
#                         cand[m,i], cand[m,j] = cand[m,j], cand[m,i]
#                 cand = cand.astype(np.uint8)
#             scores = self._score_batch(cand)
#             m = int(np.argmax(scores))
#             if scores[m] > best:
#                 k = cand[m].copy(); best = float(scores[m])
#             else:
#                 break
#         return k, best
#
#     def _select_mutator(self):
#         """Pick a mutator function based on keyops + params."""
#         if getattr(self.keyops.caps, "kind", "") != "perm":
#             return self.keyops.mutate
#         if self._perm_mutate_mix is not None and hasattr(self.keyops, "mutate_mixed"):
#             return self.keyops.mutate_mixed
#         if self._perm_block_size is not None and hasattr(self.keyops, "mutate_block_swap"):
#             return lambda k, r: self.keyops.mutate_block_swap(k, r, block_size=self._perm_block_size)
#         if self._perm_rotate_size is not None and hasattr(self.keyops, "mutate_rotate_subset"):
#             return lambda k, r: self.keyops.mutate_rotate_subset(k, r, size=self._perm_rotate_size)
#         if hasattr(self.keyops, "mutate_mixed"):
#             return self.keyops.mutate_mixed
#         return self.keyops.mutate
#
#     # ---------------- main search --------------------------------
#     def search(self) -> Solution:
#         """
#         Simulated annealing with diagnostics, elitism, and early stopping.
#
#         • Energy = -log(score+eps).
#         • Best solution is never lost (elitism).
#         • Stop when:
#             - stop_score reached
#             - no improvement for `patience` iterations
#         """
#         import math
#         rng = self._rng()
#
#         fast = self._maybe_return_test_key_fastpath("sa")
#         if fast is not None:
#             return fast
#
#         mutator = self._select_mutator()
#         if self.verbose:
#             print(f"[SA] using {len(self.seed_keys)} initial seeds")
#             print(f"[SA] keyops={self.keyops.caps.kind}/{self.keyops.caps.length}, "
#                   f"mutator={getattr(mutator, '__name__', 'fn')}")
#
#         params_for_span = {
#             "iters": int(self.iters),
#             "T0": float(self.T0),
#             "Tmin": float(self.Tmin),
#             "cooling": float(self.cooling),
#             "K": int(self.K or 0),
#         }
#         accepts, sweeps = 0, 0
#         debug_interval = 500
#
#         with TelemetrySpan(self.problem, "sa", params_for_span) as span:
#             # --- seed & score ---
#             key = self._maybe_best_of_seeds(rng).astype(np.uint8)
#             score = self._score_key(key)
#             E = self._energy(score)
#
#             best_key, best_score = key.copy(), float(score)
#
#             # initial polish
#             best_key, best_score = self._local_improve_perm(best_key, best_score, rng, rounds=2, batch_pairs=256)
#             best_key, best_score = self._local_improve_add(best_key, best_score)
#             key, score, E = best_key.copy(), float(best_score), self._energy(best_score)
#
#             if self.verbose:
#                 print(f"[SA-init] score={score:.6f} E={E:.6f}")
#
#             last_improve_it = 0
#             T = float(self.T0)
#
#             for it in range(self.iters):
#                 # propose candidate
#                 cand = mutator(key, rng).astype(np.uint8)
#                 if np.all(cand == key):
#                     cand = self.keyops.mutate(key, rng).astype(np.uint8)
#
#                 cand_score = self._score_key(cand)
#                 cand_E = self._energy(cand_score)
#
#                 # Metropolis accept
#                 delta_E = cand_E - E
#                 accepted = False
#                 if delta_E <= 0.0 or rng.random() < math.exp(-delta_E / max(T, 1e-12)):
#                     accepts += 1
#                     key, score, E = cand, cand_score, cand_E
#                     accepted = True
#                     if score > best_score + self.tol:
#                         sweeps += 1
#                         if self.local_improve_on_accept:
#                             key, score = self._local_improve_perm(key, score, rng, rounds=1, batch_pairs=128)
#                             key, score = self._local_improve_add(key, score)
#                             E = self._energy(score)
#                         best_key, best_score = key.copy(), float(score)
#                         last_improve_it = it
#
#                 # elitism safety rope
#                 if self.elitism:
#                     if self.reseed_interval > 0 and ((it + 1) % self.reseed_interval == 0):
#                         key, score = best_key.copy(), float(best_score)
#                         E = self._energy(score)
#                     if (score < best_score - self.rescue_drop_abs) or (score < best_score * self.rescue_drop_ratio):
#                         key, score = best_key.copy(), float(best_score)
#                         E = self._energy(score)
#
#                 if it % debug_interval == 0:
#                     print(f"[SA it={it:6d}] "
#                           f"T={T:.5f} curr={score:.6f} best={best_score:.6f} "
#                           f"cand={cand_score:.6f} ΔE={delta_E:.6f} "
#                           f"{'ACCEPT' if accepted else 'REJECT'}")
#
#                 # stopping checks
#                 if self.stop_score is not None and best_score >= self.stop_score:
#                     print(f"[SA-stop] reached stop_score={self.stop_score}")
#                     break
#                 if self.patience > 0 and (it - last_improve_it) >= self.patience:
#                     print(f"[SA-stop] no improvement in {self.patience} iters")
#                     break
#
#                 T = max(T * self.cooling, self.Tmin)
#
#                 if it % 1000 == 0 or it == self.iters - 1:
#                     span.progress(it=int(it), T=float(T),
#                                   score=float(score), best=float(best_score),
#                                   accepts_so_far=int(accepts), sweeps_so_far=int(sweeps),
#                                   accept_rate=float(accepts / max(1, it + 1)))
#
#             span.end(best_score=float(best_score))
#
#         pt_str = self._decrypt_to_text(best_key)
#         meta = {"optimizer": "sa", "interrupt_idx": []}
#         meta = attach_telemetry_to_meta(self.problem, meta)
#         return Solution(best_key.tolist(), pt_str, float(best_score), meta)
#
#     # def search(self) -> Solution:
#     #     """
#     #     Run simulated annealing (SA) search.
#     #
#     #     Internals:
#     #       • Acceptance is based on energy = -log(score + eps).
#     #       • Best key is tracked using raw score (higher is better).
#     #       • Telemetry and returned Solution always report raw scores.
#     #     """
#     #     import math
#     #
#     #     rng = self._rng()
#     #     fast = self._maybe_return_test_key_fastpath("sa")
#     #     if fast is not None:
#     #         return fast
#     #
#     #     mutator = self._select_mutator()
#     #     if self.verbose:
#     #         print(f"[SA] using {len(self.seed_keys)} initial seeds")
#     #         print(f"[SA] keyops={self.keyops.caps.kind}/{self.keyops.caps.length}, "
#     #               f"mutator={getattr(mutator, '__name__', 'fn')}")
#     #
#     #     params_for_span = {
#     #         "iters": int(self.iters),
#     #         "T0": float(self.T0),
#     #         "Tmin": float(self.Tmin),
#     #         "cooling": float(self.cooling),
#     #         "K": int(self.K or 0),
#     #     }
#     #     accepts, sweeps = 0, 0
#     #
#     #     with TelemetrySpan(self.problem, "sa", params_for_span) as span:
#     #         # --- initial key from seeds or random ---
#     #         key = self._maybe_best_of_seeds(rng).astype(np.uint8)
#     #         score = self._score_key(key)
#     #         E = self._energy(score)
#     #
#     #         best_key, best_score = key.copy(), float(score)
#     #
#     #         # optional polish
#     #         best_key, best_score = self._local_improve_perm(best_key, best_score, rng, rounds=2, batch_pairs=256)
#     #         best_key, best_score = self._local_improve_add(best_key, best_score)
#     #         key, score, E = best_key.copy(), float(best_score), self._energy(best_score)
#     #
#     #         T = float(self.T0)
#     #         for it in range(self.iters):
#     #             cand = mutator(key, rng).astype(np.uint8)
#     #             if np.all(cand == key):
#     #                 cand = self.keyops.mutate(key, rng).astype(np.uint8)
#     #
#     #             cand_score = self._score_key(cand)
#     #             cand_E = self._energy(cand_score)
#     #
#     #             delta_E = cand_E - E
#     #             if delta_E <= 0.0 or rng.random() < math.exp(-delta_E / max(T, 1e-12)):
#     #                 accepts += 1
#     #                 key, score, E = cand, cand_score, cand_E
#     #                 if score > best_score:
#     #                     sweeps += 1
#     #                     if self.local_improve_on_accept:
#     #                         key, score = self._local_improve_perm(key, score, rng, rounds=1, batch_pairs=128)
#     #                         key, score = self._local_improve_add(key, score)
#     #                         E = self._energy(score)
#     #                     best_key, best_score = key.copy(), float(score)
#     #
#     #             if self.stop_score is not None and best_score >= self.stop_score:
#     #                 break
#     #
#     #             T = max(T * self.cooling, self.Tmin)
#     #
#     #             if it % 1000 == 0 or it == self.iters - 1:
#     #                 span.progress(
#     #                     it=int(it), T=float(T),
#     #                     score=float(score), best=float(best_score),
#     #                     accepts_so_far=int(accepts), sweeps_so_far=int(sweeps),
#     #                     accept_rate=float(accepts / max(1, it+1)),
#     #                 )
#     #
#     #         span.end(best_score=float(best_score))
#     #
#     #     pt_str = self._decrypt_to_text(best_key)
#     #     meta = {"optimizer": "sa", "interrupt_idx": []}
#     #     meta = attach_telemetry_to_meta(self.problem, meta)
#     #     return Solution(best_key.tolist(), pt_str, float(best_score), meta)
#
#     # def search(self) -> Solution:
#     #     rng = self._rng()
#     #     fast = self._maybe_return_test_key_fastpath("sa")
#     #     if fast is not None:
#     #         return fast
#     #
#     #     mutator = self._select_mutator()
#     #     if self.verbose:
#     #         print(f"[SA] keyops={self.keyops.caps.kind}/{self.keyops.caps.length}, "
#     #               f"mutator={getattr(mutator, '__name__', 'fn')}")
#     #
#     #     params_for_span = {"iters": int(self.iters),
#     #                        "T0": float(self.T0), "Tmin": float(self.Tmin),
#     #                        "cooling": float(self.cooling),
#     #                        "K": int(self.K or 0)}
#     #     accepts, sweeps = 0, 0
#     #
#     #     with TelemetrySpan(self.problem, "sa", params_for_span) as span:
#     #         key = self._maybe_best_of_seeds(rng).astype(np.uint8)
#     #         score = self._score_key(key)
#     #         best_key, best_score = key.copy(), float(score)
#     #
#     #         # quick polish
#     #         best_key, best_score = self._local_improve_perm(best_key, best_score, rng, rounds=2, batch_pairs=256)
#     #         best_key, best_score = self._local_improve_add(best_key, best_score)
#     #         key, score = best_key.copy(), float(best_score)
#     #
#     #         T = float(self.T0)
#     #         for it in range(self.iters):
#     #             cand = mutator(key, rng).astype(np.uint8)
#     #             if np.all(cand == key):  # force movement
#     #                 cand = self.keyops.mutate(key, rng).astype(np.uint8)
#     #
#     #             cand_score = self._score_key(cand)
#     #             delta = cand_score - score
#     #             if delta >= 0.0 or rng.random() < np.exp(delta / max(T, 1e-12)):
#     #                 accepts += 1
#     #                 key, score = cand, cand_score
#     #                 if score > best_score:
#     #                     sweeps += 1
#     #                     if self.local_improve_on_accept:
#     #                         key, score = self._local_improve_perm(key, score, rng, rounds=1, batch_pairs=128)
#     #                         key, score = self._local_improve_add(key, score)
#     #                     best_key, best_score = key.copy(), float(score)
#     #
#     #             if self.stop_score is not None and best_score >= self.stop_score:
#     #                 break
#     #
#     #             T = max(T * self.cooling, self.Tmin)
#     #
#     #             if it % 1000 == 0 or it == self.iters - 1:
#     #                 span.progress(it=int(it), T=float(T),
#     #                               score=float(score), best=float(best_score),
#     #                               accepts_so_far=int(accepts), sweeps_so_far=int(sweeps),
#     #                               accept_rate=float(accepts / max(1, it+1)))
#     #
#     #         span.end(best_score=float(best_score))
#     #
#     #     pt_str = self._decrypt_to_text(best_key)
#     #     meta = {"optimizer": "sa", "interrupt_idx": []}
#     #     meta = attach_telemetry_to_meta(self.problem, meta)
#     #     return Solution(best_key.tolist(), pt_str, float(best_score), meta)
#
#
#
#
#
# # # # ============================================================
# # # # rune_decrypter_prime/optimizers/sa_optimizer.py
# # # #   Simulated Annealing (device-agnostic, KeyOps-driven)
# # # # ============================================================
# # from __future__ import annotations
# # from typing import Optional
# # import numpy as np
# #
# # from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
# # from rune_decrypter_prime.core.config import OptimizerConfig
# # from rune_decrypter_prime.core.config import Solution
# # from rune_decrypter_prime.core.problem import DecryptionProblem
# # from rune_decrypter_prime.utils.runeglish import Runeglish
# # from rune_decrypter_prime.core.telemetry_helpers import (
# #     TelemetrySpan, attach_telemetry_to_meta
# # )
# #
# # ArrayU8 = np.ndarray
# #
# #
# # class SAOptimizer(OptimizerBase):
# #     """
# #     Simulated Annealing over the cipher's key space via cipher.keyops.
# #
# #     Device-agnostic: all scoring goes through problem.evaluate_keys(keys_2d).
# #     The problem/scorer decide CPU vs Torch vs CUDA; the optimizer stays NumPy.
# #
# #     API-compatible with Beam/GA:
# #       - __init__(problem, cfg_cipher, **params)
# #       - optional engine hooks: set_interrupt_idx / set_interrupt_search_space / set_transposition_modes
# #       - search() -> Solution(key=list[uint8], plaintext=str, score=float, meta=dict)
# #
# #     Params (OptimizerConfig.params):
# #       sa_init_temp: float = 1.0
# #       sa_min_temp : float = 1e-3
# #       sa_cooling  : float = 0.995          # if sa_auto_cooling=False, used directly
# #       sa_auto_cooling: bool = True         # if True, set cooling so T(iters)=Tmin
# #       sa_iters    : int   = 10000
# #       verbose     : bool  = False
# #       seed        : int|None = None
# #       initial_keys: List[key] | None       # optional seeds (we pick the best)
# #       test_key    : key | None             # fast-path: score+return without search
# #       stop_score  : float|None = None
# #     """
# #
# #     def __init__(self, problem: DecryptionProblem, opt_cfg: OptimizerConfig):
# #         super().__init__(problem, opt_cfg)
# #
# #         # ----- params -----
# #         self.T0           = self.get_param("sa_init_temp", 1.0)
# #         self.Tmin         = self.get_param("sa_min_temp", 1e-3)
# #         self.cooling      = self.get_param("sa_cooling", 0.995)
# #         self.auto_cooling = bool(self.get_param("sa_auto_cooling", True))
# #         self.iters        = int(self.get_param("sa_iters", 10_000))
# #         self.stop_score   = self.get_param("stop_score", None)
# #
# #         # optional engine hooks (kept for parity; unused here)
# #         self._interrupt_idx: Optional[np.ndarray] = None
# #         self._intr_pool: Optional[np.ndarray] = None
# #         self._intr_max: Optional[int] = None
# #         self._t_modes = None
# #
# #         self._perm_mutate_mix = self.get_param("perm_mutate_mix", None)  # (0.7,0.2,0.1)
# #         self._perm_block_size = self.get_param("perm_block_size", None)  # int
# #         self._perm_rotate_size = self.get_param("perm_rotate_size", None)  # int
# #
# #         # If requested, calibrate the geometric cooling so T_end = Tmin at iters
# #         if self.auto_cooling and self.T0 > 0 and self.Tmin > 0 and self.iters > 0:
# #             # cooling^iters = Tmin/T0  →  cooling = (Tmin/T0)^(1/iters)
# #             self.cooling = float((self.Tmin / self.T0) ** (1.0 / float(self.iters)))
# #
# #     # -------------- engine hooks (optional) ---------------------
# #     def set_interrupt_idx(self, idx: np.ndarray | None):
# #         self._interrupt_idx = None if idx is None else np.asarray(idx, np.intp)
# #
# #     def set_interrupt_search_space(self, pool, max_count):
# #         self._intr_pool = None if pool is None else np.asarray(pool, np.intp)
# #         self._intr_max  = None if max_count is None else int(max_count)
# #
# #     def set_transposition_modes(self, modes):
# #         self._t_modes = modes  # stored for future use
# #
# #     # ---------------- helpers -----------------------------------
# #     @staticmethod
# #     def _as_numpy(x) -> np.ndarray:
# #         """Best-effort conversion to NumPy (handles torch/cupy)."""
# #         try:
# #             if hasattr(x, "detach") and hasattr(x, "cpu") and hasattr(x, "numpy"):
# #                 return x.detach().cpu().numpy()
# #             if hasattr(x, "get"):
# #                 import numpy as _np
# #                 return _np.asarray(x.get())
# #         except Exception:
# #             pass
# #         import numpy as _np
# #         return _np.asarray(x)
# #
# #     def _score_key(self, key_u8: np.ndarray) -> float:
# #         out = self.problem.evaluate_keys(key_u8[None, :])
# #         arr = self._as_numpy(out)
# #         return float(arr[0])
# #
# #     def _score_batch(self, keys_2d: np.ndarray) -> np.ndarray:
# #         out = self.problem.evaluate_keys(keys_2d)
# #         return self._as_numpy(out)
# #
# #     def _decrypt_to_text(self, key_u8: np.ndarray) -> str:
# #         pt_idx = self.problem.cipher.decrypt(key=key_u8, ciphertext=self._ct)[0]
# #         return Runeglish.to_rune(pt_idx, self._wli)
# #
# #     def _maybe_best_of_seeds(self, rng: np.random.Generator) -> np.ndarray:
# #         """
# #         If initial seeds were provided, score them all (batch) and start from the best.
# #         Always normalize through keyops to ensure a valid key (esp. for permutations).
# #         """
# #         if not self.seed_keys:
# #             return self.keyops.random(rng).astype(np.uint8)
# #
# #         # normalize all seeds and unique them to avoid redundant scoring
# #         keys = [self.keyops.normalize(np.asarray(k, np.uint8)).astype(np.uint8) for k in self.seed_keys]
# #         if len(keys) > 1:
# #             # drop exact duplicates
# #             uniq = []
# #             seen = set()
# #             for k in keys:
# #                 t = tuple(int(x) for x in k)
# #                 if t not in seen:
# #                     seen.add(t)
# #                     uniq.append(k)
# #             keys = uniq
# #
# #         batch = np.stack(keys, axis=0).astype(np.uint8)  # [N,K]
# #         scores = self._score_batch(batch)                # [N]
# #         j = int(np.argmax(scores))
# #         return batch[j].copy()
# #
# #     def _local_improve_add(self, key: np.ndarray, score: float) -> tuple[np.ndarray, float]:
# #         """Greedy sweep for additive keys (unchanged)."""
# #         if getattr(self.keyops.caps, "kind", "") != "additive":
# #             return key, float(score)
# #
# #         k = self.keyops.normalize(key).copy()
# #         best = float(score)
# #         A = getattr(self.problem.cipher, "A", 29)
# #         K = k.size
# #
# #         for col in range(K):
# #             batch = np.tile(k, (A, 1)).astype(np.uint8)  # [A,K]
# #             batch[:, col] = np.arange(A, dtype=np.uint8)
# #             scores = self._score_batch(batch)           # [A]
# #             j = int(np.argmax(scores))
# #             if scores[j] > best:
# #                 k[col] = np.uint8(j)
# #                 best = float(scores[j])
# #         return k, best
# #
# #     def _local_improve_perm(self, key: np.ndarray, score: float, rng: np.random.Generator,
# #                             rounds: int = 3, batch_pairs: int = 256) -> tuple[np.ndarray, float]:
# #         """
# #         Fast 2-swap hill-climb for permutation keys:
# #           - Propose 'batch_pairs' random index pairs; score all swapped keys in one batch.
# #           - Take the best if it improves; repeat for a small number of rounds.
# #         Uses keyops.batch_2swap_candidates if available.
# #         """
# #         if getattr(self.keyops.caps, "kind", "") != "perm":
# #             return key, float(score)
# #
# #         k = self.keyops.normalize(key).astype(np.uint8).copy()
# #         best = float(score)
# #
# #         has_batch = hasattr(self.keyops, "batch_2swap_candidates")
# #         K = int(k.size)
# #
# #         for _ in range(max(1, rounds)):
# #             # build random pairs
# #             pairs = np.column_stack([rng.integers(0, K, size=batch_pairs),
# #                                      rng.integers(0, K, size=batch_pairs)]).astype(np.int64)
# #             if has_batch:
# #                 cand = self.keyops.batch_2swap_candidates(k, pairs)  # [M,K]
# #             else:
# #                 # fallback: manually build small batch
# #                 M = int(batch_pairs)
# #                 cand = np.tile(k[None, :], (M, 1))
# #                 for m in range(M):
# #                     i, j = int(pairs[m,0]), int(pairs[m,1])
# #                     if i != j:
# #                         cand[m, i], cand[m, j] = cand[m, j], cand[m, i]
# #                 cand = cand.astype(np.uint8)
# #
# #             scores = self._score_batch(cand)             # [M]
# #             m = int(np.argmax(scores))
# #             if scores[m] > best:
# #                 k = cand[m].copy()
# #                 best = float(scores[m])
# #             else:
# #                 break  # plateau
# #         return k, best
# #
# #     def search(self) -> Solution:
# #         """
# #         Run simulated annealing (SA) search to recover the key and plaintext.
# #
# #         Contract:
# #           - Deterministic: seeded rng; no hidden randomness.
# #           - Telemetry: wrapped in TelemetrySpan, records progress every 1000 iters
# #           - Device/scoring/dtype: delegated to scorer/cipher.
# #         """
# #         rng = self._rng()
# #         fast = self._maybe_return_test_key_fastpath("sa")
# #         if fast is not None:
# #             return fast
# #
# #         # optional per-run tuning of permutation neighbourhood
# #         if getattr(self.keyops.caps, "kind", "") == "perm":
# #             if self._perm_mutate_mix is not None:
# #                 setattr(self.keyops, "_mutate_mix", tuple(self._perm_mutate_mix))
# #             if self._perm_block_size is not None:
# #                 setattr(self.keyops, "_block_size", int(self._perm_block_size))
# #             if self._perm_rotate_size is not None:
# #                 setattr(self.keyops, "_rotate_size", int(self._perm_rotate_size))
# #
# #         # Mutator choice: use richer neighbourhood if provided by KeyOps
# #         mutator = getattr(self.keyops, "mutate_mixed", self.keyops.mutate)
# #         if self.verbose:
# #             print(f"[SA] keyops={self.keyops.caps.kind}/{self.keyops.caps.length}, "
# #                   f"mutator={getattr(mutator, '__name__', 'fn')}")
# #         # --- Telemetry span setup ------------------------------------------------
# #         params_for_span = {
# #             "iters": int(self.iters),
# #             "T0": float(self.T0),
# #             "Tmin": float(self.Tmin),
# #             "cooling": float(self.cooling),
# #             "K": int(self.K or 0),
# #         }
# #         accepts = 0
# #         sweeps = 0
# #
# #         # --- Main annealing loop -------------------------------------------------
# #         with TelemetrySpan(self.problem, "sa", params_for_span) as span:
# #             # choose best starting key across all provided seeds (or random)
# #             key = self._maybe_best_of_seeds(rng).astype(np.uint8)
# #
# #             score = self._score_key(key)
# #             best_key, best_score = key.copy(), float(score)
# #
# #             # one-time quick polish of the starting key (perm/additive specific)
# #             best_key, best_score = self._local_improve_perm(best_key, best_score, rng, rounds=2, batch_pairs=256)
# #             best_key, best_score = self._local_improve_add(best_key, best_score)
# #
# #             key, score = best_key.copy(), float(best_score)
# #
# #             T = float(self.T0)
# #             for it in range(self.iters):
# #                 cand = mutator(key, rng).astype(np.uint8)
# #                 cand_score = self._score_key(cand)
# #
# #                 delta = cand_score - score
# #                 if delta >= 0.0 or rng.random() < np.exp(delta / max(T, 1e-12)):
# #                     accepts += 1
# #                     key, score = cand, cand_score
# #                     if score > best_score:
# #                         sweeps += 1
# #                         # small local polish around improvements
# #                         key, score = self._local_improve_perm(key, score, rng, rounds=1, batch_pairs=128)
# #                         key, score = self._local_improve_add(key, score)
# #                         best_key, best_score = key.copy(), float(score)
# #
# #                 if self.stop_score is not None and best_score >= self.stop_score:
# #                     break
# #
# #                 T = max(T * self.cooling, self.Tmin)
# #
# #                 if it % 1000 == 0 or it == self.iters - 1:
# #                     if self.verbose:
# #                         print(f"[SA it={it}] T={T:.4g} score={float(score):.6f} best={best_score:.6f}")
# #                     span.progress(
# #                         it=int(it),
# #                         T=float(T),
# #                         score=float(score),
# #                         best=float(best_score),
# #                         accepts_so_far=int(accepts),
# #                         sweeps_so_far=int(sweeps),
# #                     )
# #
# #             span.end(best_score=float(best_score))
# #
# #         # --- Final decrypt & telemetry attach -----------------------------------
# #         pt_str = self._decrypt_to_text(best_key)
# #         meta = {"optimizer": "sa", "interrupt_idx": []}
# #         meta = attach_telemetry_to_meta(self.problem, meta)
# #
# #         return Solution(best_key.tolist(), pt_str, float(best_score), meta)
# #
