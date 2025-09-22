# # ============================================================
# # rune_decrypter_prime/optimizers/ga_optimizer.py
# #   KeyOps-driven Genetic Algorithm (device-agnostic)
# # ============================================================
# ============================================================
# rune_decrypter_prime/optimizers/ga_optimizer.py
#   Genetic Algorithm (permutation/additive safe)
# ============================================================
from __future__ import annotations
import numpy as np

from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
from rune_decrypter_prime.core.config import OptimizerConfig, Solution
from rune_decrypter_prime.core.telemetry_helpers import (
    TelemetrySpan, attach_telemetry_to_meta
)


class GAOptimizer(OptimizerBase):
    """
    Genetic Algorithm over the cipher key space.

    Params (OptimizerConfig.params)
    --------------------------------
    pop_size      : int   = 128
    generations   : int   = 150
    elite_frac    : float = 0.05
    cx_frac       : float = 0.8
    mut_prob      : float = 0.25
    tournament_k  : int   = 3
    plateau_gens  : int   = 0     # 0 disables plateau early-stop
    perm_batch_improve_rounds : int = 2
    perm_batch_improve_size   : int = 256
    local_improve_iters : int = 0  # reserved (not used directly here)

    Common:
    seed, initial_keys, test_key, stop_score, verbose, log_interval
    """

    def __init__(self, problem, opt_cfg: OptimizerConfig):
        super().__init__(problem, opt_cfg)
        self.pop_size = int(self.get_param("pop_size", 128))
        self.generations = int(self.get_param("generations", 150))
        self.elite_frac = float(self.get_param("elite_frac", 0.05))
        self.cx_frac = float(self.get_param("cx_frac", 0.8))
        self.mut_prob = float(self.get_param("mut_prob", 0.25))
        self.tournament_k = int(self.get_param("tournament_k", 3))
        self.plateau_gens = int(self.get_param("plateau_gens", 0))
        self.perm_batch_improve_rounds = int(self.get_param("perm_batch_improve_rounds", 2))
        self.perm_batch_improve_size = int(self.get_param("perm_batch_improve_size", 256))

        # Invariants
        if self.pop_size < 4:
            raise ValueError("pop_size must be >= 4")
        self.n_elite = max(2, int(round(self.elite_frac * self.pop_size)))

    # ---------------- Permutation operators (internal, safe) ----------------
    def _pmx(self, p1: np.ndarray, p2: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Partially Mapped Crossover (PMX) for permutations."""
        n = p1.size
        a, b = sorted(rng.integers(0, n, size=2).tolist())
        child = np.full(n, 255, dtype=np.uint8)

        # copy segment from p1
        child[a:b] = p1[a:b]
        # mapping from p1 segment to p2 segment
        map_src = p2[a:b]
        map_dst = p1[a:b]

        def map_val(v):
            # Follow mapping until a free spot is reached
            while True:
                # if v collides with existing child position -> remap
                mask = (map_src == v)
                if not mask.any():
                    return v
                v = map_dst[mask.nonzero()[0][0]]

        # fill remaining positions from p2 with mapping
        for i in list(range(0, a)) + list(range(b, n)):
            v = p2[i]
            v = map_val(int(v))
            if v in child:
                # find a missing symbol
                missing = np.setdiff1d(np.arange(n, dtype=np.uint8), child, assume_unique=False)
                if missing.size > 0:
                    v = int(missing[0])
            child[i] = np.uint8(v)

        return child

    def _ox(self, p1: np.ndarray, p2: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Order Crossover (OX) for permutations."""
        n = p1.size
        a, b = sorted(rng.integers(0, n, size=2).tolist())
        child = np.full(n, 255, dtype=np.uint8)
        child[a:b] = p1[a:b]
        # order from p2 skipping already present
        fill = [v for v in p2.tolist() if v not in child[a:b].tolist()]
        pos = list(range(0, a)) + list(range(b, n))
        for i, v in zip(pos, fill):
            child[i] = np.uint8(v)
        return child

    def _mutate_perm(self, k: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """2-swap mutation (single or double swap with small prob)."""
        out = k.copy()
        n = out.size
        i, j = int(rng.integers(0, n)), int(rng.integers(0, n))
        if i != j:
            out[i], out[j] = out[j], out[i]
        # small chance of a second swap
        if rng.random() < 0.25:
            i2, j2 = int(rng.integers(0, n)), int(rng.integers(0, n))
            if i2 != j2:
                out[i2], out[j2] = out[j2], out[i2]
        return out

    # ---------------- Population helpers ----------------
    def _seed_population(self, rng: np.random.Generator) -> np.ndarray:
        """
        Deterministic population seeding:
        - First slots are unique provided seeds (normalised)
        - Remaining filled with random valid keys
        """
        uniq, seen = [], set()
        for k in self.seed_keys:
            t = tuple(int(x) for x in k[:self.K])
            if t not in seen:
                seen.add(t); uniq.append(self.keyops.normalize(k)[:self.K])
        base = np.asarray(uniq, dtype=np.uint8) if uniq else np.zeros((0, self.K), dtype=np.uint8)

        needed = self.pop_size - base.shape[0]
        if needed > 0:
            rand = [self.keyops.random(rng).astype(np.uint8)[:self.K] for _ in range(needed)]
            if base.size == 0:
                pop = np.stack(rand, axis=0)
            else:
                pop = np.vstack([base, np.stack(rand, axis=0)])
        else:
            pop = base[:self.pop_size, :]

        return np.ascontiguousarray(pop, dtype=np.uint8)

    def _crossover(self, p1: np.ndarray, p2: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Choose PMX or OX randomly for permutations; else fallback to keyops.crossover or copy."""
        if getattr(self.keyops.caps, "kind", "") == "perm":
            if rng.random() < 0.5:
                child = self._pmx(p1, p2, rng)
            else:
                child = self._ox(p1, p2, rng)
            # safety repair (ensure bijection 0..K-1 if alphabet size==K)
            # For general alphabets, trust normalize() to enforce validity.
            child = self.keyops.normalize(child).astype(np.uint8)
            return child
        # non-permutation keys: try keyops.crossover if present; else take p1
        if hasattr(self.keyops, "crossover"):
            return self.keyops.crossover(p1, p2, rng).astype(np.uint8)
        return p1.copy()

    def _mutate(self, k: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        if getattr(self.keyops.caps, "kind", "") == "perm":
            return self._mutate_perm(k, rng)
        return self.keyops.mutate(k, rng).astype(np.uint8)

    def _tournament(self, scores: np.ndarray, rng: np.random.Generator) -> int:
        n = scores.size
        idx = rng.integers(0, n, size=self.tournament_k)
        j = int(np.argmax(scores[idx]))
        return int(idx[j])

    def search(self) -> Solution:
        rng = self.rng

        fast = self._maybe_return_test_key_fastpath("ga")
        if fast is not None:
            return fast



        params_for_span = {
            "pop": int(self.pop_size),
            "gens": int(self.generations),
            "elite": int(self.n_elite),
            "cx_frac": float(self.cx_frac),
            "mut_prob": float(self.mut_prob),
            "K": int(self.K),
        }

        if self.verbose:
            print(f"[GA-init] pop={self.pop_size} gens={self.generations} "
                  f"seeds_used={len(self.seed_keys)} stop_score={self.stop_score}")

        # 5% progress step (20 chunks). Always ≥1.
        pct_step = max(1, self.generations // 20)

        with TelemetrySpan(self.problem, "ga", params_for_span) as span:
            pop = self._seed_population(rng)  # [P,K]
            scores = self._score_batch(pop)   # [P]
            order = np.argsort(scores)[::-1]
            pop, scores = pop[order], scores[order]
            best_key = pop[0].copy()
            best_score = float(scores[0])
            plateau_left = self.plateau_gens

            # quick local polish on best
            best_key, best_score = self._local_improve_perm(best_key, best_score, rng,
                                                            rounds=self.perm_batch_improve_rounds,
                                                            batch_pairs=self.perm_batch_improve_size)
            best_key, best_score = self._local_improve_add(best_key, best_score)
            if best_score > float(scores[0]):
                pop[0], scores[0] = best_key.copy(), float(best_score)

            for gen in range(self.generations):
                # Stop on target score
                if self.stop_score is not None and best_score >= self.stop_score:
                    if self.verbose:
                        print(f"[GA-stop] reached stop_score={self.stop_score}")
                    break

                P = pop.shape[0]
                n_cx = int(round(self.cx_frac * (P - self.n_elite)))
                n_mut_candidates = P - self.n_elite - n_cx
                if n_cx % 2 == 1:
                    n_cx -= 1
                    n_mut_candidates += 1

                # Elites
                next_pop = [pop[i].copy() for i in range(self.n_elite)]

                # Crossover
                for _ in range(n_cx // 2):
                    p1 = pop[self._tournament(scores, rng)]
                    p2 = pop[self._tournament(scores, rng)]
                    c1 = self._crossover(p1, p2, rng)
                    c2 = self._crossover(p2, p1, rng)
                    next_pop.extend([c1, c2])

                # Mutation
                for _ in range(n_mut_candidates):
                    p = pop[self._tournament(scores, rng)]
                    c = p.copy()
                    if rng.random() < self.mut_prob:
                        c = self._mutate(c, rng)
                    next_pop.append(self.keyops.normalize(c).astype(np.uint8))

                pop = np.ascontiguousarray(np.stack(next_pop, axis=0), dtype=np.uint8)  # [P,K]
                scores = self._score_batch(pop)
                order = np.argsort(scores)[::-1]
                pop, scores = pop[order], scores[order]

                # Track best + optional polish-on-improve
                if scores[0] > best_score:
                    best_key = pop[0].copy()
                    best_score = float(scores[0])
                    best_key, best_score = self._local_improve_perm(best_key, best_score, rng, rounds=1, batch_pairs=128)
                    best_key, best_score = self._local_improve_add(best_key, best_score)
                    if best_score > float(scores[0]):
                        pop[0], scores[0] = best_key.copy(), float(best_score)
                    plateau_left = self.plateau_gens
                else:
                    if self.plateau_gens > 0:
                        plateau_left -= 1
                        if plateau_left <= 0:
                            if self.verbose:
                                print(f"[GA] plateau for {self.plateau_gens} gens; stopping")
                            break



                # Telemetry & friendly progress printing
                should_log = (
                    (self.log_interval and gen % self.log_interval == 0)
                    or (gen % pct_step == 0)
                    or (gen == self.generations - 1)
                )
                if should_log:
                    mean_now = float(np.mean(scores))
                    top5_now = float(np.mean(scores[:5])) if scores.size >= 5 else mean_now
                    pct = 100.0 * (gen + 1) / max(1, self.generations)
                    if self.verbose:
                        # kid-friendly, compact progress line
                        print(f"[GA {pct:5.1f}%] gen={gen:4d}  best={best_score:.6f}  mean={mean_now:.6f}  top5={top5_now:.6f}")
                    span.progress(gen=int(gen), best=float(best_score), mean=mean_now, top5=top5_now)

            span.end(best_score=float(best_score))

        pt_str = self._decrypt_to_text(best_key)
        meta = {"optimizer": "ga", "interrupt_idx": []}
        meta = attach_telemetry_to_meta(self.problem, meta)
        return Solution(best_key.tolist(), pt_str, float(best_score), meta)


# from __future__ import annotations
# import numpy as np
#
# from rune_decrypter_prime.core.problem import DecryptionProblem
# from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
# from rune_decrypter_prime.core.config import Solution, OptimizerConfig
# from rune_decrypter_prime.utils.runeglish import Runeglish
# from rune_decrypter_prime.core.telemetry_helpers import (
#     TelemetrySpan, attach_telemetry_to_meta
# )
#
# ArrayU8 = np.ndarray
#
#
# class GAOptimizer(OptimizerBase):
#     """
#     Generic GA over arbitrary key spaces using cipher.keyops.
#
#     Device-agnostic: all scoring goes through problem.evaluate_keys(keys_2d).
#     The problem/scorer decide CPU vs Torch vs CUDA; the optimizer stays NumPy.
#
#     Requirements from cipher.keyops (permutation variant shown):
#       • random(rng) -> (K,)
#       • normalize(key|(B,K)) -> same shape, valid keys
#       • mutate(key,rng) -> (K,)
#         Optional richer ops if present:
#           - mutate_k_swaps(key,rng,k)
#           - mutate_block_swap(...), mutate_cycle3(...),
#             mutate_rotate_subset(...), mutate_mixed(...)
#           - crossover(p1,p2,rng)  # e.g., OX
#           - batch_2swap_candidates(base,pairs)  # batch hillclimb helper
#       • keyops.caps.kind == "perm" (or "additive" for additive path)
#       • keyops.caps.length == K
#
#     Optimizer params (opt_cfg.params):
#       pop_size: int = 128
#       generations: int = 200
#       elite_frac: float = 0.05                 # ∈ [0, 0.5]
#       cx_frac: float = 0.70                    # ∈ [0, 1]
#       mut_prob: float = 0.30                   # per-child mutation probability
#       tournament_k: int = 3
#
#       # Seed control
#       initial_keys: Optional[List[List[int]]]  # from UI; merged by base class
#       test_key: Optional[List[int]]
#
#       # Stopping
#       stop_score: Optional[float]
#
#       # Local improvements for permutations
#       local_improve_iters: int = 200
#       local_improve_k: int = 1
#       perm_batch_improve_size: int = 64
#       perm_batch_improve_rounds: int = 3
#
#       # Perm mutator selection (only if the op exists on keyops)
#       #   'mixed' | 'swap' | 'k_swaps' | 'block' | 'cycle3' | 'rotate'  (default: smart auto)
#       perm_mutator: Optional[str] = None
#       perm_k_swaps: Optional[int] = None  # used only with 'k_swaps'
#     """
#
#     def __init__(self, problem: DecryptionProblem, opt_cfg: OptimizerConfig):
#         super().__init__(problem, opt_cfg)
#
#         # --- GA knobs ----------------------------------------------------------
#         self.pop_size     = int(self.get_param("pop_size", 128))
#         self.generations  = int(self.get_param("generations", 50))
#         self.elite_frac   = float(self.get_param("elite_frac", 0.05))
#         self.cx_frac      = float(self.get_param("cx_frac", 0.70))
#
#         m = self.get_param("mut_prob", 0.30)
#         try: m = float(m)
#         except Exception: m = 0.30
#         self.mut_prob     = max(0.0, min(1.0, m))
#
#         self.tournament_k = int(self.get_param("tournament_k", 3)) or 3
#         if self.tournament_k < 2:
#             self.tournament_k = 2
#
#         # Local improvements
#         self.local_improve_iters  = int(self.get_param("local_improve_iters", 200))
#         self.local_improve_k      = int(self.get_param("local_improve_k", 1))
#         self.perm_batch_improve_size   = int(self.get_param("perm_batch_improve_size", 64))
#         self.perm_batch_improve_rounds = int(self.get_param("perm_batch_improve_rounds", 3))
#
#         # Mutator selection (by name) — only used if the op actually exists
#         self.perm_mutator  = str(self.get_param("perm_mutator", "") or "").lower()
#         self.perm_k_swaps  = self.get_param("perm_k_swaps", None)
#
#         # Sanity clamps
#         if not (0.0 <= self.elite_frac <= 0.5):
#             self.elite_frac = min(0.5, max(0.0, self.elite_frac))
#         if not (0.0 <= self.cx_frac <= 1.0):
#             self.cx_frac = min(1.0, max(0.0, self.cx_frac))
#
#         if self.verbose:
#             print(f"▶ GA pop={self.pop_size} gen={self.generations} K={self.K} "
#                   f"cx={self.cx_frac:.2f} mut={self.mut_prob:.2f} tk={self.tournament_k}")
#
#         # Choose a mutation function compatible with available keyops
#         self._mutate = self._select_mutator()
#
#     # ---------- Optional engine hooks (parity with Beam/SA) ----------
#     def set_interrupt_idx(self, idx: np.ndarray | None):       # not used
#         pass
#     def set_interrupt_search_space(self, pool, max_count):     # not used
#         pass
#     def set_transposition_modes(self, modes):                   # not used
#         pass
#
#     # ---------- Utilities ------------------------------------------------------
#
#     def _select_mutator(self):
#         """Pick a mutation function that actually exists on keyops, based on param preference."""
#         kops = self.keyops
#         want = self.perm_mutator
#
#         # Helper wrappers (each returns a function f(key,rng)->key)
#         def _swap():      return lambda k,r: (kops.mutate(k, r) if hasattr(kops, "mutate") else k.copy())
#         def _mixed():     return (lambda k,r: kops.mutate_mixed(k, r)) if hasattr(kops, "mutate_mixed") else _swap()
#         def _cycle3():    return (lambda k,r: kops.mutate_cycle3(k, r)) if hasattr(kops, "mutate_cycle3") else _swap()
#         def _block():     return (lambda k,r: kops.mutate_block_swap(k, r)) if hasattr(kops, "mutate_block_swap") else _swap()
#         def _rotate():    return (lambda k,r: kops.mutate_rotate_subset(k, r)) if hasattr(kops, "mutate_rotate_subset") else _swap()
#         def _k_swaps():
#             k = int(self.perm_k_swaps or max(1, self.local_improve_k))
#             if hasattr(kops, "mutate_k_swaps"):
#                 return lambda key, rng: kops.mutate_k_swaps(key, rng, k=k)
#             return _swap()
#
#         # Honor requested mutator if possible
#         if want == "mixed":   return _mixed()
#         if want == "swap":    return _swap()
#         if want == "k_swaps": return _k_swaps()
#         if want == "block":   return _block()
#         if want == "cycle3":  return _cycle3()
#         if want == "rotate":  return _rotate()
#
#         # Auto: prefer mutate_mixed if present, otherwise fall back to mutate
#         return _mixed() if hasattr(kops, "mutate_mixed") else _swap()
#
#     def _score_batch(self, keys_2d: np.ndarray) -> np.ndarray:
#         keys_2d = np.asarray(keys_2d, dtype=np.uint8, order="C")
#         return np.asarray(self.problem.evaluate_keys(keys_2d))
#
#     @staticmethod
#     def _as_numpy(x) -> np.ndarray:
#         """Best-effort conversion to a NumPy array (handles torch/cupy)."""
#         try:
#             if hasattr(x, "detach") and hasattr(x, "cpu") and hasattr(x, "numpy"):
#                 return x.detach().cpu().numpy()   # torch
#             if hasattr(x, "get"):
#                 import numpy as _np
#                 return _np.asarray(x.get())       # cupy
#         except Exception:
#             pass
#         import numpy as _np
#         return _np.asarray(x)
#
#     def _init_population(self, rng: np.random.Generator) -> np.ndarray:
#         pop = np.empty((self.pop_size, self.K), dtype=np.uint8)
#
#         # Seed rows first (verbatim after normalize)
#         s = 0
#         for sk in self.seed_keys:
#             if s >= self.pop_size:
#                 break
#             k = self.keyops.normalize(np.asarray(sk, dtype=np.uint8))
#             if k.size != self.K:
#                 continue
#             pop[s] = k
#             s += 1
#
#         # Random fill remainder
#         for i in range(s, self.pop_size):
#             pop[i] = self.keyops.random(rng)
#
#         # Ensure every row is a valid key
#         return self.keyops.normalize(pop)
#
#     def _tournament(self, scores: np.ndarray, rng: np.random.Generator, k: int | None = None) -> int:
#         kk = int(k or self.tournament_k)
#         idx = rng.integers(0, scores.size, size=kk)
#         sub = scores[idx]
#         return int(idx[int(np.argmax(sub))])
#
#     # ---------- Local improvements ---------------------------------------------
#
#     def _local_improve_perm_batch(
#         self,
#         key: np.ndarray,
#         score: float,
#         rng: np.random.Generator,
#         batch_size: int | None = None,
#         rounds: int | None = None,
#     ) -> tuple[np.ndarray, float]:
#         if getattr(self.keyops.caps, "kind", "") != "perm":
#             return key, float(score)
#
#         B = int(batch_size or self.perm_batch_improve_size)
#         R = int(rounds or self.perm_batch_improve_rounds)
#         if B <= 0 or R <= 0:
#             return key, float(score)
#
#         best_k = key.copy()
#         best_s = float(score)
#
#         for _ in range(R):
#             pairs = rng.integers(0, self.K, size=(B, 2))
#             if hasattr(self.keyops, "batch_2swap_candidates"):
#                 cand = self.keyops.batch_2swap_candidates(best_k, pairs)
#             else:
#                 cand = np.tile(best_k[None, :], (B, 1))
#                 for m in range(B):
#                     i, j = int(pairs[m, 0]), int(pairs[m, 1])
#                     if i != j:
#                         cand[m, i], cand[m, j] = cand[m, j], cand[m, i]
#             sc = self._as_numpy(self._score_batch(cand))
#             j = int(np.argmax(sc))
#             if sc[j] > best_s:
#                 best_s = float(sc[j]); best_k = cand[j].copy()
#             else:
#                 break  # early exit if a whole round had no gain
#
#         return best_k, best_s
#
#     def _local_improve_perm(self, key: np.ndarray, score: float, rng: np.random.Generator) -> tuple[np.ndarray, float]:
#         if getattr(self.keyops.caps, "kind", "") != "perm":
#             return key, float(score)
#
#         best_k = key.copy()
#         best_s = float(score)
#         n = best_k.size
#         if n < 2 or self.local_improve_iters <= 0:
#             return best_k, best_s
#
#         cand = best_k.copy()
#         for _ in range(self.local_improve_iters):
#             cand[:] = best_k
#             for _sw in range(max(1, self.local_improve_k)):
#                 i, j = rng.integers(0, n, size=2)
#                 cand[i], cand[j] = cand[j], cand[i]
#             sc = float(self._score_batch(cand[None, :])[0])
#             if sc > best_s:
#                 best_s = sc; best_k = cand.copy()
#         return best_k, best_s
#
#     def _local_improve_add(self, key: np.ndarray, score: float, sweeps: int = 1) -> tuple[np.ndarray, float]:
#         if getattr(self.keyops.caps, "kind", "") != "additive":
#             return key, float(score)
#         k = self.keyops.normalize(key).copy()
#         best = float(score)
#         A = getattr(self.problem.cipher, "A", 29)
#         K = k.size
#         batch = np.tile(k, (A, 1)).astype(np.uint8)
#         for _ in range(max(1, sweeps)):
#             improved = False
#             for col in range(K):
#                 batch[:, col] = np.arange(A, dtype=np.uint8)
#                 scores = self._as_numpy(self._score_batch(batch))
#                 j = int(np.argmax(scores))
#                 if scores[j] > best:
#                     k[col] = np.uint8(j); best = float(scores[j]); improved = True
#             if not improved:
#                 break
#         return k, best
#
#     # ---------- Main search -----------------------------------------------------
#
#     def search(self) -> Solution:
#         rng = self._rng()
#
#         fast = self._maybe_return_test_key_fastpath("ga")
#         if fast is not None:
#             return fast
#
#         # Fast path for explicit test_key
#         if self.test_key is not None:
#             k = self.keyops.normalize(self.test_key)[: self.K].astype(np.uint8)
#             if k.size != self.K:
#                 raise ValueError("test_key length != GA K")
#             score = float(self._score_batch(k[None, :])[0])
#             pt_idx = self.problem.cipher.decrypt(key=k, ciphertext=self._ct)[0]
#             return Solution(
#                 k.tolist(),
#                 Runeglish.to_rune(pt_idx, self._wli),
#                 score,
#                 {"optimizer": "ga", "reason": "test_key"},
#             )
#
#         params_for_span = {
#             "seed": int(self.seed) if self.seed is not None else None,
#             "pop_size": int(self.pop_size),
#             "generations": int(self.generations),
#             "elite_frac": float(self.elite_frac),
#             "cx_frac": float(self.cx_frac),
#             "mut_prob": float(self.mut_prob),
#             "K": int(self.K),
#         }
#
#         with TelemetrySpan(self.problem, "ga", params_for_span) as span:
#             pop = self._init_population(rng)
#             scores = self._as_numpy(self._score_batch(pop))
#
#             span.progress(gen=0,
#                           best=float(scores.max(initial=-1e9)),
#                           mean=float(scores.mean() if scores.size else 0.0))
#
#             best_i = int(np.argmax(scores))
#             best_key = pop[best_i].copy()
#             best_score = float(scores[best_i])
#
#             if self.verbose:
#                 print(f"[GA] init best={best_score:.6f}")
#
#             for gen in range(self.generations):
#                 if self.log_interval and (gen % self.log_interval == 0):
#                     print(f"[GA] gen={gen:4d} best={float(np.max(scores)):.4f}")
#
#                 # ---- Elites ----------------------------------------------------
#                 elite_n = max(1, int(self.elite_frac * self.pop_size))
#                 elite_idx = np.argpartition(scores, -elite_n)[-elite_n:]
#                 elites = pop[elite_idx].copy()
#
#                 # ---- Children --------------------------------------------------
#                 off_n = self.pop_size - elite_n
#                 children = np.empty((off_n, self.K), dtype=np.uint8)
#                 cx_n = int(self.cx_frac * off_n)
#
#                 # crossover kids
#                 has_cx = hasattr(self.keyops, "crossover")
#                 for i in range(cx_n):
#                     if has_cx:
#                         p1 = pop[self._tournament(scores, rng)]
#                         p2 = pop[self._tournament(scores, rng)]
#                         child = self.keyops.crossover(p1, p2, rng)
#                     else:
#                         p1 = pop[self._tournament(scores, rng)]
#                         child = p1.copy()
#                     # mutation pass (probabilistic)
#                     if rng.random() < self.mut_prob:
#                         child = self._mutate(child, rng)
#                     children[i] = self.keyops.normalize(child)
#
#                 # fill rest: mutated parents or randoms
#                 changed_cnt = 0
#                 for i in range(cx_n, off_n):
#                     if rng.random() < 0.85:
#                         p = pop[self._tournament(scores, rng)]
#                         child = self._mutate(p, rng)
#                         changed_cnt += int(np.any(child != p))
#                     else:
#                         child = self.keyops.random(rng)
#                         changed_cnt += 1
#                     children[i] = self.keyops.normalize(child)
#
#                 # ---- Next generation ------------------------------------------
#                 prev_best = float(scores.max(initial=-1e9))
#                 pop = np.vstack([elites, children])
#                 scores = self._as_numpy(self._score_batch(pop))
#
#                 # progress
#                 if (self.verbose and (gen % max(1, self.generations // 10) == 0)) or (gen == self.generations - 1):
#                     span.progress(
#                         gen=int(gen + 1),
#                         best=float(scores.max(initial=-1e9)),
#                         mean=float(scores.mean() if scores.size else 0.0),
#                         mut_rate=float(changed_cnt / max(1, off_n - cx_n)),
#                     )
#
#                 # update global best
#                 bi = int(np.argmax(scores))
#                 if scores[bi] > best_score:
#                     best_score = float(scores[bi]); best_key = pop[bi].copy()
#
#                 # optional local improvements
#                 if getattr(self.keyops.caps, "kind", "") == "perm":
#                     best_key, best_score = self._local_improve_perm_batch(
#                         best_key, best_score, rng,
#                         batch_size=self.perm_batch_improve_size,
#                         rounds=self.perm_batch_improve_rounds,
#                     )
#                     best_key, best_score = self._local_improve_perm(best_key, best_score, rng)
#
#                 if getattr(self.keyops.caps, "kind", "") == "additive":
#                     best_key, best_score = self._local_improve_add(best_key, best_score, sweeps=2)
#
#                 if self.stop_score is not None and best_score >= self.stop_score:
#                     if self.verbose:
#                         print(f"[GA] early stop: best >= {self.stop_score}")
#                     break
#
#             # Final polish
#             if getattr(self.keyops.caps, "kind", "") == "additive":
#                 best_key, best_score = self._local_improve_add(best_key, best_score, sweeps=2)
#             if getattr(self.keyops.caps, "kind", "") == "perm":
#                 best_key, best_score = self._local_improve_perm_batch(
#                     best_key, best_score, rng,
#                     batch_size=self.perm_batch_improve_size,
#                     rounds=self.perm_batch_improve_rounds,
#                 )
#                 best_key, best_score = self._local_improve_perm(best_key, best_score, rng)
#
#             span.end(best_score=float(best_score))
#
#         # Final decrypt & meta
#         pt_idx = self.problem.cipher.decrypt(key=best_key, ciphertext=self._ct)
#         pt_idx = np.asarray(pt_idx, dtype=np.uint8).tolist()  # ensure iterable ints
#         pt_str = Runeglish.to_rune(pt_idx, self._wli)
#
#         meta = {"optimizer": "ga", "interrupt_idx": []}
#         meta = attach_telemetry_to_meta(self.problem, meta)
#
#         return Solution(best_key.tolist(), pt_str, float(best_score), meta)
#
# # # ============================================================
# # # rune_decrypter_prime/optimizers/ga_optimizer.py
# # #   KeyOps-driven Genetic Algorithm (device-agnostic)
# # # ============================================================
# #
# # from __future__ import annotations
# # import numpy as np
# #
# # from rune_decrypter_prime.core.problem import DecryptionProblem
# # from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
# # from rune_decrypter_prime.core.config import Solution, OptimizerConfig
# # from rune_decrypter_prime.utils.runeglish import Runeglish
# # from rune_decrypter_prime.core.telemetry_helpers import (
# #     TelemetrySpan, attach_telemetry_to_meta
# # )
# #
# # ArrayU8 = np.ndarray
# #
# #
# # class GAOptimizer(OptimizerBase):
# #     """
# #     Genetic Algorithm (GA) for solving decryption problems over arbitrary key
# #     spaces. This implementation is device-agnostic: it delegates scoring to
# #     `problem.evaluate_keys(keys_2d)`, which may run on CPU, Torch, or CUDA.
# #
# #     The optimizer itself is pure NumPy and only depends on the cipher's keyops.
# #
# #     --------------------------------------------------------------------------
# #     KeyOps requirements (permutation variant shown)
# #     --------------------------------------------------------------------------
# #     • random(rng) -> (K,)
# #     • normalize(key|(B,K)) -> same shape, valid keys
# #     • mutate(key,rng) -> (K,)
# #       Optional richer ops if present:
# #         - mutate_k_swaps(key,rng,k)
# #         - mutate_block_swap(...), mutate_cycle3(...),
# #           mutate_rotate_subset(...), mutate_mixed(...)
# #         - crossover(p1,p2,rng)  # e.g. OX
# #         - batch_2swap_candidates(base,pairs)  # batch hillclimb helper
# #     • keyops.caps.kind == "perm" (or "additive" for additive path)
# #     • keyops.caps.length == K
# #
# #     --------------------------------------------------------------------------
# #     Optimizer parameters (opt_cfg.params)
# #     --------------------------------------------------------------------------
# #     pop_size: int = 128
# #         Number of individuals in the population.
# #     generations: int = 200
# #         Number of generations to evolve.
# #     elite_frac: float = 0.05
# #         Fraction of elites (best solutions) copied verbatim each generation.
# #     cx_frac: float = 0.70
# #         Fraction of offspring produced by crossover (vs. mutation/random).
# #     mut_prob: float = 0.30
# #         Probability of applying mutation to each offspring.
# #     tournament_k: int = 3
# #         Tournament size for parent selection.
# #
# #     # Seed / test control
# #     initial_keys: Optional[List[List[int]]]
# #         Optional seed keys to inject into the initial population.
# #     test_key: Optional[List[int]]
# #         If provided, bypasses GA and scores this key only.
# #
# #     # Stopping
# #     stop_score: Optional[float]
# #         If best_score ≥ stop_score, terminate early.
# #
# #     # Local improvements
# #     local_improve_iters: int = 200
# #     local_improve_k: int = 1
# #     perm_batch_improve_size: int = 64
# #     perm_batch_improve_rounds: int = 3
# #
# #     # Perm mutator selection
# #     perm_mutator: Optional[str] = None
# #         'mixed' | 'swap' | 'k_swaps' | 'block' | 'cycle3' | 'rotate'
# #     perm_k_swaps: Optional[int] = None
# #         Used only with 'k_swaps'.
# #
# #     # Logging
# #     log_interval: Optional[int] = None
# #         If verbose=True, print human-readable progress every N generations.
# #         Defaults to ~10 logs across the full run.
# #     """
# #     # ============================================================
# #     # rune_decrypter_prime/optimizers/ga_optimizer.py
# #     #   KeyOps-driven Genetic Algorithm (device-agnostic)
# #     # ============================================================
# #     from __future__ import annotations
# #     import numpy as np
# #
# #     from rune_decrypter_prime.core.problem import DecryptionProblem
# #     from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
# #     from rune_decrypter_prime.core.config import Solution, OptimizerConfig
# #     from rune_decrypter_prime.utils.runeglish import Runeglish
# #     from rune_decrypter_prime.core.telemetry_helpers import (
# #         TelemetrySpan, attach_telemetry_to_meta
# #     )
# #
# #     ArrayU8 = np.ndarray
# #
# #     class GAOptimizer(OptimizerBase):
# #         """
# #         Generic GA over arbitrary key spaces using cipher.keyops.
# #
# #         Device-agnostic: all scoring goes through problem.evaluate_keys(keys_2d).
# #         The problem/scorer decide CPU vs Torch vs CUDA; the optimizer stays NumPy.
# #
# #         Requirements from cipher.keyops (permutation variant shown):
# #           • random(rng) -> (K,)
# #           • normalize(key|(B,K)) -> same shape, valid keys
# #           • mutate(key,rng) -> (K,)
# #             Optional richer ops if present:
# #               - mutate_k_swaps(key,rng,k)
# #               - mutate_block_swap(...), mutate_cycle3(...),
# #                 mutate_rotate_subset(...), mutate_mixed(...)
# #               - crossover(p1,p2,rng)  # e.g., OX
# #               - batch_2swap_candidates(base,pairs)  # batch hillclimb helper
# #           • keyops.caps.kind == "perm" (or "additive" for additive path)
# #           • keyops.caps.length == K
# #
# #         Optimizer params (opt_cfg.params):
# #           pop_size: int = 128
# #           generations: int = 200
# #           elite_frac: float = 0.05                 # ∈ [0, 0.5]
# #           cx_frac: float = 0.70                    # ∈ [0, 1]
# #           mut_prob: float = 0.30                   # per-child mutation probability
# #           tournament_k: int = 3
# #
# #           # Seed control
# #           initial_keys: Optional[List[List[int]]]  # from UI; merged by base class
# #           test_key: Optional[List[int]]
# #
# #           # Stopping
# #           stop_score: Optional[float]
# #
# #           # Local improvements for permutations
# #           local_improve_iters: int = 200
# #           local_improve_k: int = 1
# #           perm_batch_improve_size: int = 64
# #           perm_batch_improve_rounds: int = 3
# #
# #           # Perm mutator selection (only if the op exists on keyops)
# #           #   'mixed' | 'swap' | 'k_swaps' | 'block' | 'cycle3' | 'rotate'  (default: smart auto)
# #           perm_mutator: Optional[str] = None
# #           perm_k_swaps: Optional[int] = None  # used only with 'k_swaps'
# #         """
# #
# #         def __init__(self, problem: DecryptionProblem, opt_cfg: OptimizerConfig):
# #             super().__init__(problem, opt_cfg)
# #
# #             # --- GA knobs ----------------------------------------------------------
# #             self.pop_size = int(self.get_param("pop_size", 128))
# #             self.generations = int(self.get_param("generations", 50))
# #             self.elite_frac = float(self.get_param("elite_frac", 0.05))
# #             self.cx_frac = float(self.get_param("cx_frac", 0.70))
# #
# #             m = self.get_param("mut_prob", 0.30)
# #             try:
# #                 m = float(m)
# #             except Exception:
# #                 m = 0.30
# #             self.mut_prob = max(0.0, min(1.0, m))
# #
# #             self.tournament_k = int(self.get_param("tournament_k", 3)) or 3
# #             if self.tournament_k < 2:
# #                 self.tournament_k = 2
# #
# #             # Local improvements
# #             self.local_improve_iters = int(self.get_param("local_improve_iters", 200))
# #             self.local_improve_k = int(self.get_param("local_improve_k", 1))
# #             self.perm_batch_improve_size = int(self.get_param("perm_batch_improve_size", 64))
# #             self.perm_batch_improve_rounds = int(self.get_param("perm_batch_improve_rounds", 3))
# #
# #             # Mutator selection (by name) — only used if the op actually exists
# #             self.perm_mutator = str(self.get_param("perm_mutator", "") or "").lower()
# #             self.perm_k_swaps = self.get_param("perm_k_swaps", None)
# #
# #             # Sanity clamps
# #             if not (0.0 <= self.elite_frac <= 0.5):
# #                 self.elite_frac = min(0.5, max(0.0, self.elite_frac))
# #             if not (0.0 <= self.cx_frac <= 1.0):
# #                 self.cx_frac = min(1.0, max(0.0, self.cx_frac))
# #
# #             if self.verbose:
# #                 print(f"▶ GA pop={self.pop_size} gen={self.generations} K={self.K} "
# #                       f"cx={self.cx_frac:.2f} mut={self.mut_prob:.2f} tk={self.tournament_k}")
# #
# #             # Choose a mutation function compatible with available keyops
# #             self._mutate = self._select_mutator()
# #
# #         # ---------- Optional engine hooks (parity with Beam/SA) ----------
# #         def set_interrupt_idx(self, idx: np.ndarray | None):  # not used
# #             pass
# #
# #         def set_interrupt_search_space(self, pool, max_count):  # not used
# #             pass
# #
# #         def set_transposition_modes(self, modes):  # not used
# #             pass
# #
# #         # ---------- Utilities ------------------------------------------------------
# #
# #         def _select_mutator(self):
# #             """Pick a mutation function that actually exists on keyops, based on param preference."""
# #             kops = self.keyops
# #             want = self.perm_mutator
# #
# #             # Helper wrappers (each returns a function f(key,rng)->key)
# #             def _swap():
# #                 return lambda k, r: (kops.mutate(k, r) if hasattr(kops, "mutate") else k.copy())
# #
# #             def _mixed():
# #                 return (lambda k, r: kops.mutate_mixed(k, r)) if hasattr(kops, "mutate_mixed") else _swap()
# #
# #             def _cycle3():
# #                 return (lambda k, r: kops.mutate_cycle3(k, r)) if hasattr(kops, "mutate_cycle3") else _swap()
# #
# #             def _block():
# #                 return (lambda k, r: kops.mutate_block_swap(k, r)) if hasattr(kops, "mutate_block_swap") else _swap()
# #
# #             def _rotate():
# #                 return (lambda k, r: kops.mutate_rotate_subset(k, r)) if hasattr(kops,
# #                                                                                  "mutate_rotate_subset") else _swap()
# #
# #             def _k_swaps():
# #                 k = int(self.perm_k_swaps or max(1, self.local_improve_k))
# #                 if hasattr(kops, "mutate_k_swaps"):
# #                     return lambda key, rng: kops.mutate_k_swaps(key, rng, k=k)
# #                 return _swap()
# #
# #             # Honor requested mutator if possible
# #             if want == "mixed":   return _mixed()
# #             if want == "swap":    return _swap()
# #             if want == "k_swaps": return _k_swaps()
# #             if want == "block":   return _block()
# #             if want == "cycle3":  return _cycle3()
# #             if want == "rotate":  return _rotate()
# #
# #             # Auto: prefer mutate_mixed if present, otherwise fall back to mutate
# #             return _mixed() if hasattr(kops, "mutate_mixed") else _swap()
# #
# #         def _score_batch(self, keys_2d: np.ndarray) -> np.ndarray:
# #             keys_2d = np.asarray(keys_2d, dtype=np.uint8, order="C")
# #             return np.asarray(self.problem.evaluate_keys(keys_2d))
# #
# #         @staticmethod
# #         def _as_numpy(x) -> np.ndarray:
# #             """Best-effort conversion to a NumPy array (handles torch/cupy)."""
# #             try:
# #                 if hasattr(x, "detach") and hasattr(x, "cpu") and hasattr(x, "numpy"):
# #                     return x.detach().cpu().numpy()  # torch
# #                 if hasattr(x, "get"):
# #                     import numpy as _np
# #                     return _np.asarray(x.get())  # cupy
# #             except Exception:
# #                 pass
# #             import numpy as _np
# #             return _np.asarray(x)
# #
# #         def _init_population(self, rng: np.random.Generator) -> np.ndarray:
# #             pop = np.empty((self.pop_size, self.K), dtype=np.uint8)
# #
# #             # Seed rows first (verbatim after normalize)
# #             s = 0
# #             for sk in self.seed_keys:
# #                 if s >= self.pop_size:
# #                     break
# #                 k = self.keyops.normalize(np.asarray(sk, dtype=np.uint8))
# #                 if k.size != self.K:
# #                     continue
# #                 pop[s] = k
# #                 s += 1
# #
# #             # Random fill remainder
# #             for i in range(s, self.pop_size):
# #                 pop[i] = self.keyops.random(rng)
# #
# #             # Ensure every row is a valid key
# #             return self.keyops.normalize(pop)
# #
# #         def _tournament(self, scores: np.ndarray, rng: np.random.Generator, k: int | None = None) -> int:
# #             kk = int(k or self.tournament_k)
# #             idx = rng.integers(0, scores.size, size=kk)
# #             sub = scores[idx]
# #             return int(idx[int(np.argmax(sub))])
# #
# #         # ---------- Local improvements ---------------------------------------------
# #
# #         def _local_improve_perm_batch(
# #                 self,
# #                 key: np.ndarray,
# #                 score: float,
# #                 rng: np.random.Generator,
# #                 batch_size: int | None = None,
# #                 rounds: int | None = None,
# #         ) -> tuple[np.ndarray, float]:
# #             if getattr(self.keyops.caps, "kind", "") != "perm":
# #                 return key, float(score)
# #
# #             B = int(batch_size or self.perm_batch_improve_size)
# #             R = int(rounds or self.perm_batch_improve_rounds)
# #             if B <= 0 or R <= 0:
# #                 return key, float(score)
# #
# #             best_k = key.copy()
# #             best_s = float(score)
# #
# #             for _ in range(R):
# #                 pairs = rng.integers(0, self.K, size=(B, 2))
# #                 if hasattr(self.keyops, "batch_2swap_candidates"):
# #                     cand = self.keyops.batch_2swap_candidates(best_k, pairs)
# #                 else:
# #                     cand = np.tile(best_k[None, :], (B, 1))
# #                     for m in range(B):
# #                         i, j = int(pairs[m, 0]), int(pairs[m, 1])
# #                         if i != j:
# #                             cand[m, i], cand[m, j] = cand[m, j], cand[m, i]
# #                 sc = self._as_numpy(self._score_batch(cand))
# #                 j = int(np.argmax(sc))
# #                 if sc[j] > best_s:
# #                     best_s = float(sc[j]);
# #                     best_k = cand[j].copy()
# #                 else:
# #                     break  # early exit if a whole round had no gain
# #
# #             return best_k, best_s
# #
# #         def _local_improve_perm(self, key: np.ndarray, score: float, rng: np.random.Generator) -> tuple[
# #             np.ndarray, float]:
# #             if getattr(self.keyops.caps, "kind", "") != "perm":
# #                 return key, float(score)
# #
# #             best_k = key.copy()
# #             best_s = float(score)
# #             n = best_k.size
# #             if n < 2 or self.local_improve_iters <= 0:
# #                 return best_k, best_s
# #
# #             cand = best_k.copy()
# #             for _ in range(self.local_improve_iters):
# #                 cand[:] = best_k
# #                 for _sw in range(max(1, self.local_improve_k)):
# #                     i, j = rng.integers(0, n, size=2)
# #                     cand[i], cand[j] = cand[j], cand[i]
# #                 sc = float(self._score_batch(cand[None, :])[0])
# #                 if sc > best_s:
# #                     best_s = sc;
# #                     best_k = cand.copy()
# #             return best_k, best_s
# #
# #         def _local_improve_add(self, key: np.ndarray, score: float, sweeps: int = 1) -> tuple[np.ndarray, float]:
# #             if getattr(self.keyops.caps, "kind", "") != "additive":
# #                 return key, float(score)
# #             k = self.keyops.normalize(key).copy()
# #             best = float(score)
# #             A = getattr(self.problem.cipher, "A", 29)
# #             K = k.size
# #             batch = np.tile(k, (A, 1)).astype(np.uint8)
# #             for _ in range(max(1, sweeps)):
# #                 improved = False
# #                 for col in range(K):
# #                     batch[:, col] = np.arange(A, dtype=np.uint8)
# #                     scores = self._as_numpy(self._score_batch(batch))
# #                     j = int(np.argmax(scores))
# #                     if scores[j] > best:
# #                         k[col] = np.uint8(j);
# #                         best = float(scores[j]);
# #                         improved = True
# #                 if not improved:
# #                     break
# #             return k, best
# #
# #         # ---------- Main search -----------------------------------------------------
# #
# #         def search(self) -> Solution:
# #             rng = self._rng()
# #
# #             fast = self._maybe_return_test_key_fastpath("ga")
# #             if fast is not None:
# #                 return fast
# #
# #             # Fast path for explicit test_key
# #             if self.test_key is not None:
# #                 k = self.keyops.normalize(self.test_key)[: self.K].astype(np.uint8)
# #                 if k.size != self.K:
# #                     raise ValueError("test_key length != GA K")
# #                 score = float(self._score_batch(k[None, :])[0])
# #                 pt_idx = self.problem.cipher.decrypt(key=k, ciphertext=self._ct)[0]
# #                 return Solution(
# #                     k.tolist(),
# #                     Runeglish.to_rune(pt_idx, self._wli),
# #                     score,
# #                     {"optimizer": "ga", "reason": "test_key"},
# #                 )
# #
# #             params_for_span = {
# #                 "seed": int(self.seed) if self.seed is not None else None,
# #                 "pop_size": int(self.pop_size),
# #                 "generations": int(self.generations),
# #                 "elite_frac": float(self.elite_frac),
# #                 "cx_frac": float(self.cx_frac),
# #                 "mut_prob": float(self.mut_prob),
# #                 "K": int(self.K),
# #             }
# #
# #             with TelemetrySpan(self.problem, "ga", params_for_span) as span:
# #                 pop = self._init_population(rng)
# #                 scores = self._as_numpy(self._score_batch(pop))
# #
# #                 span.progress(gen=0,
# #                               best=float(scores.max(initial=-1e9)),
# #                               mean=float(scores.mean() if scores.size else 0.0))
# #
# #                 best_i = int(np.argmax(scores))
# #                 best_key = pop[best_i].copy()
# #                 best_score = float(scores[best_i])
# #
# #                 if self.verbose:
# #                     print(f"[GA] init best={best_score:.6f}")
# #
# #                 for gen in range(self.generations):
# #                     if self.log_interval and (gen % self.log_interval == 0):
# #                         print(f"[GA] gen={gen:4d} best={float(np.max(scores)):.4f}")
# #
# #                     # ---- Elites ----------------------------------------------------
# #                     elite_n = max(1, int(self.elite_frac * self.pop_size))
# #                     elite_idx = np.argpartition(scores, -elite_n)[-elite_n:]
# #                     elites = pop[elite_idx].copy()
# #
# #                     # ---- Children --------------------------------------------------
# #                     off_n = self.pop_size - elite_n
# #                     children = np.empty((off_n, self.K), dtype=np.uint8)
# #                     cx_n = int(self.cx_frac * off_n)
# #
# #                     # crossover kids
# #                     has_cx = hasattr(self.keyops, "crossover")
# #                     for i in range(cx_n):
# #                         if has_cx:
# #                             p1 = pop[self._tournament(scores, rng)]
# #                             p2 = pop[self._tournament(scores, rng)]
# #                             child = self.keyops.crossover(p1, p2, rng)
# #                         else:
# #                             p1 = pop[self._tournament(scores, rng)]
# #                             child = p1.copy()
# #                         # mutation pass (probabilistic)
# #                         if rng.random() < self.mut_prob:
# #                             child = self._mutate(child, rng)
# #                         children[i] = self.keyops.normalize(child)
# #
# #                     # fill rest: mutated parents or randoms
# #                     changed_cnt = 0
# #                     for i in range(cx_n, off_n):
# #                         if rng.random() < 0.85:
# #                             p = pop[self._tournament(scores, rng)]
# #                             child = self._mutate(p, rng)
# #                             changed_cnt += int(np.any(child != p))
# #                         else:
# #                             child = self.keyops.random(rng)
# #                             changed_cnt += 1
# #                         children[i] = self.keyops.normalize(child)
# #
# #                     # ---- Next generation ------------------------------------------
# #                     prev_best = float(scores.max(initial=-1e9))
# #                     pop = np.vstack([elites, children])
# #                     scores = self._as_numpy(self._score_batch(pop))
# #
# #                     # progress
# #                     if (self.verbose and (gen % max(1, self.generations // 10) == 0)) or (gen == self.generations - 1):
# #                         span.progress(
# #                             gen=int(gen + 1),
# #                             best=float(scores.max(initial=-1e9)),
# #                             mean=float(scores.mean() if scores.size else 0.0),
# #                             mut_rate=float(changed_cnt / max(1, off_n - cx_n)),
# #                         )
# #
# #                     # update global best
# #                     bi = int(np.argmax(scores))
# #                     if scores[bi] > best_score:
# #                         best_score = float(scores[bi]);
# #                         best_key = pop[bi].copy()
# #
# #                     # optional local improvements
# #                     if getattr(self.keyops.caps, "kind", "") == "perm":
# #                         best_key, best_score = self._local_improve_perm_batch(
# #                             best_key, best_score, rng,
# #                             batch_size=self.perm_batch_improve_size,
# #                             rounds=self.perm_batch_improve_rounds,
# #                         )
# #                         best_key, best_score = self._local_improve_perm(best_key, best_score, rng)
# #
# #                     if getattr(self.keyops.caps, "kind", "") == "additive":
# #                         best_key, best_score = self._local_improve_add(best_key, best_score, sweeps=2)
# #
# #                     if self.stop_score is not None and best_score >= self.stop_score:
# #                         if self.verbose:
# #                             print(f"[GA] early stop: best >= {self.stop_score}")
# #                         break
# #
# #                 # Final polish
# #                 if getattr(self.keyops.caps, "kind", "") == "additive":
# #                     best_key, best_score = self._local_improve_add(best_key, best_score, sweeps=2)
# #                 if getattr(self.keyops.caps, "kind", "") == "perm":
# #                     best_key, best_score = self._local_improve_perm_batch(
# #                         best_key, best_score, rng,
# #                         batch_size=self.perm_batch_improve_size,
# #                         rounds=self.perm_batch_improve_rounds,
# #                     )
# #                     best_key, best_score = self._local_improve_perm(best_key, best_score, rng)
# #
# #                 span.end(best_score=float(best_score))
# #
# #             # Final decrypt & meta
# #             pt_idx = self.problem.cipher.decrypt(key=best_key, ciphertext=self._ct)[0]
# #             pt_str = Runeglish.to_rune(pt_idx, self._wli)
# #
# #             meta = {"optimizer": "ga", "interrupt_idx": []}
# #             meta = attach_telemetry_to_meta(self.problem, meta)
# #
# #             return Solution(best_key.tolist(), pt_str, float(best_score), meta)
# #
# #     def __init__(self, problem: DecryptionProblem, opt_cfg: OptimizerConfig):
# #         super().__init__(problem, opt_cfg)
# #
# #         # Core GA knobs
# #         self.pop_size     = int(self.get_param("pop_size", 128))
# #         self.generations  = int(self.get_param("generations", 50))
# #         self.elite_frac   = float(self.get_param("elite_frac", 0.05))
# #         self.cx_frac      = float(self.get_param("cx_frac", 0.70))
# #
# #         m = self.get_param("mut_prob", 0.30)
# #         try:
# #             m = float(m)
# #         except Exception:
# #             m = 0.30
# #         self.mut_prob     = max(0.0, min(1.0, m))
# #
# #         self.tournament_k = int(self.get_param("tournament_k", 3)) or 3
# #         if self.tournament_k < 2:
# #             self.tournament_k = 2
# #
# #         # Local improvement knobs
# #         self.local_improve_iters  = int(self.get_param("local_improve_iters", 200))
# #         self.local_improve_k      = int(self.get_param("local_improve_k", 1))
# #         self.perm_batch_improve_size   = int(self.get_param("perm_batch_improve_size", 64))
# #         self.perm_batch_improve_rounds = int(self.get_param("perm_batch_improve_rounds", 3))
# #
# #         # Mutator selection
# #         self.perm_mutator  = str(self.get_param("perm_mutator", "") or "").lower()
# #         self.perm_k_swaps  = self.get_param("perm_k_swaps", None)
# #
# #         # Logging
# #         self.log_interval  = int(self.get_param("log_interval", max(1, self.generations // 10)))
# #
# #         # Sanity clamps
# #         if not (0.0 <= self.elite_frac <= 0.5):
# #             self.elite_frac = min(0.5, max(0.0, self.elite_frac))
# #         if not (0.0 <= self.cx_frac <= 1.0):
# #             self.cx_frac = min(1.0, max(0.0, self.cx_frac))
# #
# #         if self.verbose:
# #             print(f"[GA-init] pop={self.pop_size} gen={self.generations} K={self.K} "
# #                   f"cx={self.cx_frac:.2f} mut={self.mut_prob:.2f} tk={self.tournament_k}")
# #
# #         # Choose mutation operator
# #         self._mutate = self._select_mutator()
# #
# #     # ----------------------------------------------------------------------
# #     # Engine hooks (parity with Beam/SA; not used in GA)
# #     # ----------------------------------------------------------------------
# #     def set_interrupt_idx(self, idx: np.ndarray | None):       # not used
# #         pass
# #
# #     def set_interrupt_search_space(self, pool, max_count):     # not used
# #         pass
# #
# #     def set_transposition_modes(self, modes):                  # not used
# #         pass
# #
# #     # ----------------------------------------------------------------------
# #     # Utility functions
# #     # ----------------------------------------------------------------------
# #     def _select_mutator(self):
# #         """
# #         Select a mutation function that exists on keyops, guided by perm_mutator.
# #         Falls back to a simple swap if the requested operator is unavailable.
# #         """
# #         kops = self.keyops
# #         want = self.perm_mutator
# #
# #         def _swap():   return lambda k, r: kops.mutate(k, r) if hasattr(kops, "mutate") else k.copy()
# #         def _mixed():  return (lambda k, r: kops.mutate_mixed(k, r)) if hasattr(kops, "mutate_mixed") else _swap()
# #         def _cycle3(): return (lambda k, r: kops.mutate_cycle3(k, r)) if hasattr(kops, "mutate_cycle3") else _swap()
# #         def _block():  return (lambda k, r: kops.mutate_block_swap(k, r)) if hasattr(kops, "mutate_block_swap") else _swap()
# #         def _rotate(): return (lambda k, r: kops.mutate_rotate_subset(k, r)) if hasattr(kops, "mutate_rotate_subset") else _swap()
# #         def _k_swaps():
# #             k = int(self.perm_k_swaps or max(1, self.local_improve_k))
# #             if hasattr(kops, "mutate_k_swaps"):
# #                 return lambda key, rng: kops.mutate_k_swaps(key, rng, k=k)
# #             return _swap()
# #
# #         if want == "mixed":   return _mixed()
# #         if want == "swap":    return _swap()
# #         if want == "k_swaps": return _k_swaps()
# #         if want == "block":   return _block()
# #         if want == "cycle3":  return _cycle3()
# #         if want == "rotate":  return _rotate()
# #
# #         # Default: use mutate_mixed if present
# #         return _mixed() if hasattr(kops, "mutate_mixed") else _swap()
# #
# #     def _score_batch(self, keys_2d: np.ndarray) -> np.ndarray:
# #         """Score a batch of candidate keys using the problem API."""
# #         keys_2d = np.asarray(keys_2d, dtype=np.uint8, order="C")
# #         return np.asarray(self.problem.evaluate_keys(keys_2d))
# #
# #     @staticmethod
# #     def _as_numpy(x) -> np.ndarray:
# #         """Convert torch/cupy arrays to NumPy if needed."""
# #         try:
# #             if hasattr(x, "detach") and hasattr(x, "cpu") and hasattr(x, "numpy"):
# #                 return x.detach().cpu().numpy()   # torch
# #             if hasattr(x, "get"):
# #                 import numpy as _np
# #                 return _np.asarray(x.get())       # cupy
# #         except Exception:
# #             pass
# #         import numpy as _np
# #         return _np.asarray(x)
# #
# #     def _init_population(self, rng: np.random.Generator) -> np.ndarray:
# #         """Initialise population with seed keys (if any) plus random fill."""
# #         pop = np.empty((self.pop_size, self.K), dtype=np.uint8)
# #
# #         # Fill seeds first
# #         s = 0
# #         for sk in self.seed_keys:
# #             if s >= self.pop_size:
# #                 break
# #             k = self.keyops.normalize(np.asarray(sk, dtype=np.uint8))
# #             if k.size != self.K:
# #                 continue
# #             pop[s] = k
# #             s += 1
# #
# #         # Fill the rest randomly
# #         for i in range(s, self.pop_size):
# #             pop[i] = self.keyops.random(rng)
# #
# #         return self.keyops.normalize(pop)
# #
# #     def _tournament(self, scores: np.ndarray, rng: np.random.Generator, k: int | None = None) -> int:
# #         """Tournament selection: pick the best of k random indices."""
# #         kk = int(k or self.tournament_k)
# #         idx = rng.integers(0, scores.size, size=kk)
# #         sub = scores[idx]
# #         return int(idx[int(np.argmax(sub))])
# #
# #     # ----------------------------------------------------------------------
# #     # Local improvement helpers
# #     # ----------------------------------------------------------------------
# #     def _local_improve_perm_batch(self, key, score, rng, batch_size=None, rounds=None):
# #         """Batch 2-swap hillclimbing for permutations."""
# #         if getattr(self.keyops.caps, "kind", "") != "perm":
# #             return key, float(score)
# #
# #         B = int(batch_size or self.perm_batch_improve_size)
# #         R = int(rounds or self.perm_batch_improve_rounds)
# #         if B <= 0 or R <= 0:
# #             return key, float(score)
# #
# #         best_k, best_s = key.copy(), float(score)
# #         for _ in range(R):
# #             pairs = rng.integers(0, self.K, size=(B, 2))
# #             if hasattr(self.keyops, "batch_2swap_candidates"):
# #                 cand = self.keyops.batch_2swap_candidates(best_k, pairs)
# #             else:
# #                 cand = np.tile(best_k[None, :], (B, 1))
# #                 for m in range(B):
# #                     i, j = int(pairs[m, 0]), int(pairs[m, 1])
# #                     if i != j:
# #                         cand[m, i], cand[m, j] = cand[m, j], cand[m, i]
# #             sc = self._as_numpy(self._score_batch(cand))
# #             j = int(np.argmax(sc))
# #             if sc[j] > best_s:
# #                 best_s, best_k = float(sc[j]), cand[j].copy()
# #             else:
# #                 break
# #         return best_k, best_s
# #
# #     def _local_improve_perm(self, key, score, rng):
# #         """Simple random-swap hillclimb for permutations."""
# #         if getattr(self.keyops.caps, "kind", "") != "perm":
# #             return key, float(score)
# #
# #         best_k, best_s = key.copy(), float(score)
# #         n = best_k.size
# #         if n < 2 or self.local_improve_iters <= 0:
# #             return best_k, best_s
# #
# #         cand = best_k.copy()
# #         for _ in range(self.local_improve_iters):
# #             cand[:] = best_k
# #             for _sw in range(max(1, self.local_improve_k)):
# #                 i, j = rng.integers(0, n, size=2)
# #                 cand[i], cand[j] = cand[j], cand[i]
# #             sc = float(self._score_batch(cand[None, :])[0])
# #             if sc > best_s:
# #                 best_s, best_k = sc, cand.copy()
# #         return best_k, best_s
# #
# #     def _local_improve_add(self, key, score, sweeps=1):
# #         """Column-sweep improvement for additive key spaces."""
# #         if getattr(self.keyops.caps, "kind", "") != "additive":
# #             return key, float(score)
# #
# #         k = self.keyops.normalize(key).copy()
# #         best = float(score)
# #         A = getattr(self.problem.cipher, "A", 29)
# #         K = k.size
# #         batch = np.tile(k, (A, 1)).astype(np.uint8)
# #         for _ in range(max(1, sweeps)):
# #             improved = False
# #             for col in range(K):
# #                 batch[:, col] = np.arange(A, dtype=np.uint8)
# #                 scores = self._as_numpy(self._score_batch(batch))
# #                 j = int(np.argmax(scores))
# #                 if scores[j] > best:
# #                     k[col] = np.uint8(j)
# #                     best = float(scores[j])
# #                     improved = True
# #             if not improved:
# #                 break
# #         return k, best
# #
# #     # ----------------------------------------------------------------------
# #     # Main GA search loop
# #     # ----------------------------------------------------------------------
# #     def search(self) -> Solution:
# #         rng = self._rng()
# #
# #         fast = self._maybe_return_test_key_fastpath("ga")
# #         if fast is not None:
# #             return fast
# #
# #         # Test key shortcut
# #         if self.test_key is not None:
# #             k = self.keyops.normalize(self.test_key)[: self.K].astype(np.uint8)
# #             if k.size != self.K:
# #                 raise ValueError("test_key length != GA K")
# #             score = float(self._score_batch(k[None, :])[0])
# #             pt_idx = self.problem.cipher.decrypt(key=k, ciphertext=self._ct)[0]
# #             return Solution(
# #                 k.tolist(),
# #                 Runeglish.to_rune(pt_idx, self._wli),
# #                 score,
# #                 {"optimizer": "ga", "reason": "test_key"},
# #             )
# #
# #         params_for_span = {
# #             "seed": int(self.seed) if self.seed is not None else None,
# #             "pop_size": int(self.pop_size),
# #             "generations": int(self.generations),
# #             "elite_frac": float(self.elite_frac),
# #             "cx_frac": float(self.cx_frac),
# #             "mut_prob": float(self.mut_prob),
# #             "K": int(self.K),
# #         }
# #
# #         with TelemetrySpan(self.problem, "ga", params_for_span) as span:
# #             pop = self._init_population(rng)
# #             scores = self._as_numpy(self._score_batch(pop))
# #
# #             span.progress(gen=0,
# #                           best=float(scores.max(initial=-1e9)),
# #                           mean=float(scores.mean() if scores.size else 0.0))
# #
# #             best_i = int(np.argmax(scores))
# #             best_key = pop[best_i].copy()
# #             best_score = float(scores[best_i])
# #
# #             if self.verbose:
# #                 print(f"[GA-init] best={best_score:.6f}")
# #
# #             for gen in range(self.generations):
# #                 # ---------------- Selection & reproduction ----------------
# #                 elite_n = max(1, int(self.elite_frac * self.pop_size))
# #                 elite_idx = np.argpartition(scores, -elite_n)[-elite_n:]
# #                 elites = pop[elite_idx].copy()
# #
# #                 off_n = self.pop_size - elite_n
# #                 children = np.empty((off_n, self.K), dtype=np.uint8)
# #                 cx_n = int(self.cx_frac * off_n)
# #
# #                 # crossover children
# #                 has_cx = hasattr(self.keyops, "crossover")
# #                 for i in range(cx_n):
# #                     if has_cx:
# #                         p1 = pop[self._tournament(scores, rng)]
# #                         p2 = pop[self._tournament(scores, rng)]
# #                         child = self.keyops.crossover(p1, p2, rng)
# #                     else:
# #                         p1 = pop[self._tournament(scores, rng)]
# #                         child = p1.copy()
# #                     if rng.random() < self.mut_prob:
# #                         child = self._mutate(child, rng)
# #                     children[i] = self.keyops.normalize(child)
# #
# #                 # mutated/random children
# #                 changed_cnt = 0
# #                 for i in range(cx_n, off_n):
# #                     if rng.random() < 0.85:
# #                         p = pop[self._tournament(scores, rng)]
# #                         child = self._mutate(p, rng)
# #                         changed_cnt += int(np.any(child != p))
# #                     else:
# #                         child = self.keyops.random(rng)
# #                         changed_cnt += 1
# #                     children[i] = self.keyops.normalize(child)
# #
# #                 # ---------------- Next generation ----------------
# #                 pop = np.vstack([elites, children])
# #                 scores = self._as_numpy(self._score_batch(pop))
# #
# #                 # Update best-so-far
# #                 bi = int(np.argmax(scores))
# #                 if scores[bi] > best_score:
# #                     best_score, best_key = float(scores[bi]), pop[bi].copy()
# #
# #                 # Human-readable progress
# #                 if self.verbose and (gen % self.log_interval == 0 or gen == self.generations - 1):
# #                     print(f"[GA] gen={gen:4d} best={best_score:.6f} mean={scores.mean():.6f}")
# #
# #                 # Telemetry
# #                 if (self.verbose and (gen % max(1, self.generations // 10) == 0)) or (gen == self.generations - 1):
# #                     span.progress(
# #                         gen=int(gen + 1),
# #                         best=float(scores.max(initial=-1e9)),
# #                         mean=float(scores.mean() if scores.size else 0.0),
# #                         mut_rate=float(changed_cnt / max(1, off_n - cx_n)),
# #                     )
# #
# #                 # Optional local improvements
# #                 if getattr(self.keyops.caps, "kind", "") == "perm":
# #                     best_key
# #
# #
# # # # ============================================================
# # # # rune_decrypter_prime/optimizers/ga_optimizer.py
# # # #   KeyOps-driven Genetic Algorithm (device-agnostic)
# # # # ============================================================
# # # from __future__ import annotations
# # # import numpy as np
# # #
# # # from rune_decrypter_prime.core.problem import DecryptionProblem
# # # from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
# # # from rune_decrypter_prime.core.config import Solution, OptimizerConfig
# # # from rune_decrypter_prime.utils.runeglish import Runeglish
# # # from rune_decrypter_prime.core.telemetry_helpers import (
# # #     TelemetrySpan, attach_telemetry_to_meta
# # # )
# # #
# # # ArrayU8 = np.ndarray
# # #
# # #
# # # class GAOptimizer(OptimizerBase):
# # #     """
# # #     Genetic Algorithm over cipher key spaces (permutation / additive).
# # #
# # #     • Device-agnostic: scoring happens via problem.evaluate_keys().
# # #     • Elitism: best individual always survives to next generation.
# # #     • Early stopping:
# # #         - stop_score: end if best_score >= stop_score
# # #         - patience:   end if no improvement in N generations
# # #     • Local improvements:
# # #         - Batch swap hillclimbs for permutation keys
# # #         - Additive column sweeps for additive keys
# # #
# # #     Parameters (OptimizerConfig.params)
# # #     -----------------------------------
# # #     pop_size: int = 128
# # #     generations: int = 200
# # #     elite_frac: float = 0.05          # fraction kept verbatim
# # #     cx_frac: float = 0.70             # fraction of offspring via crossover
# # #     mut_prob: float = 0.30            # per-child mutation probability
# # #     tournament_k: int = 3             # tournament size for parent selection
# # #
# # #     initial_keys: Optional[List[List[int]]]
# # #     stop_score: Optional[float]
# # #     patience: int = 0                 # stop if no improvement for N gens
# # #
# # #     local_improve_iters: int = 200
# # #     local_improve_k: int = 1
# # #     perm_batch_improve_size: int = 64
# # #     perm_batch_improve_rounds: int = 3
# # #
# # #     perm_mutator: Optional[str] = None
# # #       # 'mixed' | 'swap' | 'k_swaps' | 'block' | 'cycle3' | 'rotate'
# # #     perm_k_swaps: Optional[int] = None
# # #     """
# # #
# # #     def __init__(self, problem: DecryptionProblem, opt_cfg: OptimizerConfig):
# # #         super().__init__(problem, opt_cfg)
# # #
# # #         # GA knobs
# # #         self.pop_size    = int(self.get_param("pop_size", 128))
# # #         self.generations = int(self.get_param("generations", 200))
# # #         self.elite_frac  = float(self.get_param("elite_frac", 0.05))
# # #         self.cx_frac     = float(self.get_param("cx_frac", 0.70))
# # #         self.mut_prob    = float(self.get_param("mut_prob", 0.30))
# # #         self.tournament_k = max(2, int(self.get_param("tournament_k", 3)))
# # #
# # #         # Early stopping
# # #         self.stop_score  = self.get_param("stop_score", None)
# # #         self.patience    = int(self.get_param("patience", 0))
# # #
# # #         # Local improvement
# # #         self.local_improve_iters       = int(self.get_param("local_improve_iters", 200))
# # #         self.local_improve_k           = int(self.get_param("local_improve_k", 1))
# # #         self.perm_batch_improve_size   = int(self.get_param("perm_batch_improve_size", 64))
# # #         self.perm_batch_improve_rounds = int(self.get_param("perm_batch_improve_rounds", 3))
# # #
# # #         # Mutator selection
# # #         self.perm_mutator  = str(self.get_param("perm_mutator", "") or "").lower()
# # #         self.perm_k_swaps  = self.get_param("perm_k_swaps", None)
# # #
# # #         # Sanity clamps
# # #         self.elite_frac = min(0.5, max(0.0, self.elite_frac))
# # #         self.cx_frac    = min(1.0, max(0.0, self.cx_frac))
# # #         self.mut_prob   = min(1.0, max(0.0, self.mut_prob))
# # #
# # #         if self.verbose:
# # #             print(f"[GA] pop={self.pop_size} gen={self.generations} "
# # #                   f"cx={self.cx_frac:.2f} mut={self.mut_prob:.2f} tk={self.tournament_k}")
# # #
# # #         self._mutate = self._select_mutator()
# # #
# # #     # ---------------------------------------------------------------
# # #     # Mutator selection
# # #     # ---------------------------------------------------------------
# # #     def _select_mutator(self):
# # #         kops = self.keyops
# # #         want = self.perm_mutator
# # #
# # #         def _swap():   return lambda k,r: kops.mutate(k, r)
# # #         def _mixed():  return lambda k,r: kops.mutate_mixed(k, r)
# # #         def _cycle3(): return lambda k,r: kops.mutate_cycle3(k, r)
# # #         def _block():  return lambda k,r: kops.mutate_block_swap(k, r)
# # #         def _rotate(): return lambda k,r: kops.mutate_rotate_subset(k, r)
# # #         def _k_swaps():
# # #             kk = int(self.perm_k_swaps or 1)
# # #             return lambda k,r: kops.mutate_k_swaps(k, r, k=kk)
# # #
# # #         table = {
# # #             "mixed": _mixed, "swap": _swap, "cycle3": _cycle3,
# # #             "block": _block, "rotate": _rotate, "k_swaps": _k_swaps,
# # #         }
# # #         if want in table and hasattr(kops, f"mutate_{want}" if want!="swap" else "mutate"):
# # #             return table[want]()
# # #         return _mixed() if hasattr(kops, "mutate_mixed") else _swap()
# # #
# # #     # ---------------------------------------------------------------
# # #     # Population init & scoring
# # #     # ---------------------------------------------------------------
# # #     def _init_population(self, rng) -> np.ndarray:
# # #         pop = np.empty((self.pop_size, self.K), dtype=np.uint8)
# # #         s = 0
# # #         for sk in self.seed_keys:
# # #             if s >= self.pop_size: break
# # #             k = self.keyops.normalize(np.asarray(sk, np.uint8))
# # #             if k.size == self.K:
# # #                 pop[s] = k; s += 1
# # #         for i in range(s, self.pop_size):
# # #             pop[i] = self.keyops.random(rng)
# # #         return self.keyops.normalize(pop)
# # #
# # #     def _score_batch(self, keys: np.ndarray) -> np.ndarray:
# # #         return np.asarray(self.problem.evaluate_keys(keys))
# # #
# # #     # ---------------------------------------------------------------
# # #     # Local improvement
# # #     # ---------------------------------------------------------------
# # #     def _local_improve_perm(self, key, score, rng):
# # #         if self.local_improve_iters <= 0: return key, score
# # #         best_k, best_s = key.copy(), float(score)
# # #         cand = best_k.copy()
# # #         for _ in range(self.local_improve_iters):
# # #             cand[:] = best_k
# # #             for _sw in range(max(1, self.local_improve_k)):
# # #                 i,j = rng.integers(0,self.K,2)
# # #                 cand[i], cand[j] = cand[j], cand[i]
# # #             sc = float(self._score_batch(cand[None,:])[0])
# # #             if sc > best_s:
# # #                 best_s, best_k = sc, cand.copy()
# # #         return best_k, best_s
# # #
# # #     def _local_improve_add(self, key, score):
# # #         if getattr(self.keyops.caps,"kind","")!="additive": return key, score
# # #         k = self.keyops.normalize(key).copy()
# # #         best = float(score)
# # #         A = getattr(self.problem.cipher,"A",29)
# # #         batch = np.tile(k,(A,1)).astype(np.uint8)
# # #         for col in range(self.K):
# # #             batch[:,col] = np.arange(A,dtype=np.uint8)
# # #             scores = self._score_batch(batch)
# # #             j = int(np.argmax(scores))
# # #             if scores[j]>best:
# # #                 k[col]=np.uint8(j); best=float(scores[j])
# # #         return k,best
# # #
# # #     # ---------------------------------------------------------------
# # #     # Main search
# # #     # ---------------------------------------------------------------
# # #     def search(self) -> Solution:
# # #         rng = self._rng()
# # #         fast = self._maybe_return_test_key_fastpath("ga")
# # #         if fast: return fast
# # #
# # #         with TelemetrySpan(self.problem,"ga",{
# # #             "pop_size":self.pop_size,"generations":self.generations,
# # #             "elite_frac":self.elite_frac,"cx_frac":self.cx_frac,
# # #             "mut_prob":self.mut_prob,"K":self.K}) as span:
# # #
# # #             pop = self._init_population(rng)
# # #             scores = self._score_batch(pop)
# # #
# # #             best_i = int(np.argmax(scores))
# # #             best_key, best_score = pop[best_i].copy(), float(scores[best_i])
# # #             last_improve_gen = 0
# # #
# # #             for gen in range(self.generations):
# # #                 elite_n = max(1,int(self.elite_frac*self.pop_size))
# # #                 elite_idx = np.argpartition(scores,-elite_n)[-elite_n:]
# # #                 elites = pop[elite_idx].copy()
# # #
# # #                 off_n = self.pop_size-elite_n
# # #                 children = np.empty((off_n,self.K),np.uint8)
# # #                 cx_n = int(self.cx_frac*off_n)
# # #
# # #                 for i in range(cx_n):
# # #                     p1 = pop[rng.integers(0,self.pop_size)]
# # #                     p2 = pop[rng.integers(0,self.pop_size)]
# # #                     if hasattr(self.keyops,"crossover"):
# # #                         child=self.keyops.crossover(p1,p2,rng)
# # #                     else:
# # #                         child=p1.copy()
# # #                     if rng.random()<self.mut_prob:
# # #                         child=self._mutate(child,rng)
# # #                     children[i]=self.keyops.normalize(child)
# # #
# # #                 for i in range(cx_n,off_n):
# # #                     p = pop[rng.integers(0,self.pop_size)]
# # #                     if rng.random()<0.85:
# # #                         child=self._mutate(p,rng)
# # #                     else:
# # #                         child=self.keyops.random(rng)
# # #                     children[i]=self.keyops.normalize(child)
# # #
# # #                 pop = np.vstack([elites,children])
# # #                 scores = self._score_batch(pop)
# # #
# # #                 bi=int(np.argmax(scores))
# # #                 if scores[bi]>best_score:
# # #                     best_key, best_score = pop[bi].copy(), float(scores[bi])
# # #                     last_improve_gen=gen
# # #
# # #                 if self.stop_score and best_score>=self.stop_score:
# # #                     if self.verbose: print(f"[GA] stop_score reached at gen={gen}")
# # #                     break
# # #                 if self.patience>0 and (gen-last_improve_gen)>=self.patience:
# # #                     if self.verbose: print(f"[GA] patience {self.patience} hit at gen={gen}")
# # #                     break
# # #
# # #                 if self.verbose and gen%max(1,self.generations//10)==0:
# # #                     print(f"[GA] gen={gen} best={best_score:.4f} mean={scores.mean():.4f}")
# # #
# # #             # Final polish
# # #             if getattr(self.keyops.caps,"kind","")=="perm":
# # #                 best_key,best_score=self._local_improve_perm(best_key,best_score,rng)
# # #             if getattr(self.keyops.caps,"kind","")=="additive":
# # #                 best_key,best_score=self._local_improve_add(best_key,best_score)
# # #
# # #             span.end(best_score=float(best_score))
# # #
# # #         pt_idx=self.problem.cipher.decrypt(key=best_key,ciphertext=self._ct)[0]
# # #         pt_str=Runeglish.to_rune(pt_idx,self._wli)
# # #         meta={"optimizer":"ga"}; meta=attach_telemetry_to_meta(self.problem,meta)
# # #         return Solution(best_key.tolist(),pt_str,float(best_score),meta)
