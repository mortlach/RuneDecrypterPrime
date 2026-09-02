# -*- coding: utf-8 -*-
"""
solver/ga.py — Vectorised GA using KeyOps + batch decrypt/score

Parity goals:
  - Population seeding respects provided seed_keys.
  - Tournament selection (default), elitism, crossover, mutation.
  - Early-stop via target score and plateau (no-improve rounds).
  - Canonical telemetry fields: generation, pop_size, evals, since_improve, best_score.
"""

from __future__ import annotations
import numpy as np

from rdp.core.config.validation import strict_positive_int
from rdp.core.types import SolverName, KEY_DTYPE
from .solver_base import SolverBase


class GASolver(SolverBase):
    name = "ga"

    def __init__(self, problem, opt_cfg=None, **kwargs):
        params = {}
        if opt_cfg is not None:
            if isinstance(opt_cfg, dict):
                params = dict(opt_cfg)
            elif hasattr(opt_cfg, "as_dict"):
                params = dict(opt_cfg.as_dict())
            else:
                params = dict(getattr(opt_cfg, "__dict__", {}))

        # Defaults (kept conservative and deterministic)
        params.setdefault("pop_size", 64)
        params.setdefault("generations", 200)
        params["generations"] = strict_positive_int(params["generations"], "generations")

        # Selection / variation
        params.setdefault("tournament_k", 3)
        params.setdefault("elite_frac", 0.05)   # keep top 5%
        params.setdefault("cx_frac", 0.5)       # fraction of new children from crossover
        params.setdefault("mut_prob", 0.15)     # mutate probability per child (delegated to keyops)

        # Plateau stopper (no-improve rounds)
        params.setdefault("plateau_rounds", 0)    # 0 = off

        rng = kwargs.get("rng")
        if rng is None:
            raise TypeError("GASolver requires rng=np.random.Generator from the engine")

        super().__init__(
            problem,
            optimizer_name=SolverName.GA,
            params=params,
            rng=rng,
            seed_keys=kwargs.get("seed_keys"),
            stop_score=kwargs.get("stop_score"),
            verbose=bool(kwargs.get("verbose", True)),
            log_interval=int(kwargs.get("log_interval", 50)),
        )

    # ---------- internals ----------

    def _select_tournament(self, scores: np.ndarray, k: int, n: int) -> np.ndarray:
        """Return indices of 'n' parents via k-way tournaments (higher-is-better)."""
        N = scores.shape[0]
        k = max(2, int(k))
        idx = np.empty((n,), dtype=np.int64)
        for i in range(n):
            cand = self.rng.integers(0, N, size=k)
            best = cand[int(np.argmax(scores[cand]))]
            idx[i] = best
        return idx

    def _recombine_batch(self, parents: np.ndarray, n_children: int) -> np.ndarray:
        """Prefer keyops.recombine; fallback to uniform crossover."""
        if "recombine" in self.keyops.caps.ops:
            # Prefer any batch-aware recombine implementations
            try:
                batch = self.keyops.recombine(parents, n_children, self.rng)
                batch = np.ascontiguousarray(batch, dtype=KEY_DTYPE)
                if batch.ndim == 2 and int(batch.shape[0]) == int(n_children):
                    return batch
            except TypeError:
                pass
            except Exception:
                pass

            # Fallback: treat recombine as pairwise (PermutationKeyOps, etc.)
            rows = []
            for _ in range(int(n_children)):
                a = parents[self.rng.integers(0, parents.shape[0])]
                b = parents[self.rng.integers(0, parents.shape[0])]
                try:
                    child = self.keyops.recombine(a, b, self.rng)
                except TypeError:
                    child = self.keyops.recombine(a, b)  # last-ditch: rng optional
                rows.append(np.ascontiguousarray(child, dtype=KEY_DTYPE))
            return np.stack(rows, axis=0).astype(KEY_DTYPE, copy=False)

        # Fallback: uniform crossover from random parent pairs
        P, K = parents.shape
        a = parents[self.rng.integers(0, P, size=n_children)]
        b = parents[self.rng.integers(0, P, size=n_children)]
        mask = self.rng.integers(0, 2, size=(n_children, K), dtype=np.uint8)
        children = (a & (mask == 0)) | (b & (mask == 1))
        return np.ascontiguousarray(children.astype(KEY_DTYPE), dtype=KEY_DTYPE)

    def _mutate_batch(self, kids: np.ndarray, mut_prob: float) -> np.ndarray:
        """Prefer keyops.mutate; fallback to replace-one-gene."""
        if "mutate" in self.keyops.caps.ops:
            try:
                mutated = self.keyops.mutate(kids, self.rng, prob=mut_prob)
                mutated = np.ascontiguousarray(mutated, dtype=KEY_DTYPE)
                if mutated.shape == kids.shape:
                    return mutated
            except TypeError:
                pass
            except Exception:
                pass

            return self._mutate_rows_with_prob(kids, mut_prob)

        # Fallback mutation: swap one random column to a random value per child
        out = kids.copy()
        n, K = out.shape
        mcount = int(np.floor(mut_prob * n))
        if mcount <= 0:
            return out
        rows = self.rng.choice(n, size=mcount, replace=False)
        cols = self.rng.integers(0, K, size=mcount)
        A = int(getattr(self.keyops.caps, "mod", 0) or 29)  # assume 29-rune if unknown
        out[rows, cols] = self.rng.integers(0, A, size=mcount, dtype=KEY_DTYPE)
        return np.ascontiguousarray(out, dtype=KEY_DTYPE)

    def _mutate_rows_with_prob(self, kids: np.ndarray, mut_prob: float) -> np.ndarray:
        """Slow-path mutate: apply keyops.mutate row-wise honoring mut_prob."""
        out = np.ascontiguousarray(kids.copy(), dtype=KEY_DTYPE)
        if mut_prob <= 0.0:
            return out
        mask = self.rng.random(out.shape[0]) < float(mut_prob)
        rows = np.nonzero(mask)[0]
        if rows.size == 0:
            return out
        for idx in rows:
            child = self.keyops.mutate(out[idx], self.rng)
            out[idx] = np.ascontiguousarray(child, dtype=KEY_DTYPE)
        return out

    # ---------- main solve ----------

    def solve(self):
        P: int = int(self.get_param("pop_size", 64))
        G: int = int(self.get_param("generations", 200))
        k_tourn: int = int(self.get_param("tournament_k", 3))
        elite_frac: float = float(self.get_param("elite_frac", 0.05))
        cx_frac: float = float(self.get_param("cx_frac", 0.5))
        mut_prob: float = float(self.get_param("mut_prob", 0.15))
        plateau_rounds: int = int(self.get_param("plateau_rounds", 0))

        self._capture_seed_quality()
        fast = self._maybe_return_test_key_fastpath(SolverName.GA)
        if fast is not None:
            return fast

        # Normalise counts
        elites = max(0, int(np.floor(elite_frac * P)))
        elites = min(elites, P - 2)  # leave room for variation
        V = max(2, P - elites)       # children to generate each generation

        self._start_span()
        total_evals = 0
        best_score = float("-inf")
        try:
            # Seed population
            seed_mask = np.zeros(P, dtype=bool)
            if self.seed_keys is not None and len(self.seed_keys) > 0:
                base = np.ascontiguousarray(self.seed_keys, dtype=KEY_DTYPE)
                if base.shape[0] < P:
                    extra = (self.keyops.make_population(P - base.shape[0], self.rng)
                             if "make_population" in self.keyops.caps.ops
                             else np.vstack([self.keyops.random(self.rng) for _ in range(P - base.shape[0])]).astype(KEY_DTYPE))
                    pop = np.ascontiguousarray(np.vstack([base, extra]), dtype=KEY_DTYPE)
                else:
                    pop = np.ascontiguousarray(base[:P], dtype=KEY_DTYPE)
                seed_rows = min(base.shape[0], P)
                seed_mask[:seed_rows] = True
            else:
                pop = (self.keyops.make_population(P, self.rng)
                       if "make_population" in self.keyops.caps.ops
                       else np.vstack([self.keyops.random(self.rng) for _ in range(P)]).astype(KEY_DTYPE))

            scores = self._score_batch(pop); total_evals += int(pop.shape[0])
            if seed_mask.any():
                try:
                    seed_scores = scores[seed_mask]
                    rand_scores = scores[~seed_mask] if (~seed_mask).any() else None
                    payload = {
                        "population": P,
                        "seed_count": int(seed_mask.sum()),
                        "seed_best_score": float(np.max(seed_scores)),
                        "seed_mean_score": float(np.mean(seed_scores)),
                    }
                    if rand_scores is not None and rand_scores.size:
                        payload["random_best_score"] = float(np.max(rand_scores))
                        payload["random_mean_score"] = float(np.mean(rand_scores))
                    self._append_seed_diag("ga_initial", payload)
                except Exception:
                    pass
            order = np.argsort(scores)[::-1]
            pop, scores = pop[order], scores[order]
            best_key, best_score = pop[0].copy(), float(scores[0])

            # Set up plateau tracking
            self._early_stop_reset(initial_best=best_score,
                                   plateau_override=plateau_rounds)

            self._maybe_update_hamming_progress(0.0)
            for gen in range(1, G + 1):
                self._maybe_update_hamming_progress(gen / float(G))
                # Elitism
                elites_idx = np.arange(elites) if elites > 0 else np.empty((0,), dtype=np.int64)
                elite_keys = pop[elites_idx] if elites > 0 else pop[:0]

                # Parents via tournament
                parents_needed = max(2, V)  # at least 2 to recombine
                parent_idx = self._select_tournament(scores, k=k_tourn, n=parents_needed)
                parents = pop[parent_idx]

                # Variation: crossover then mutation
                n_cx = max(0, int(np.floor(cx_frac * V)))
                n_mut_only = V - n_cx

                children = []
                if n_cx > 0:
                    kids_cx = self._recombine_batch(parents, n_children=n_cx)
                    children.append(kids_cx)
                if n_mut_only > 0:
                    # pick random parents then mutate
                    base_mut = parents[self.rng.integers(0, parents.shape[0], size=n_mut_only)]
                    children.append(base_mut)

                if children:
                    children = np.ascontiguousarray(np.vstack(children), dtype=KEY_DTYPE)
                    children = self._mutate_batch(children, mut_prob=mut_prob)
                else:
                    # very small populations: force some mutation of elites
                    base_mut = pop[:max(2, V)].copy()
                    children = self._mutate_batch(base_mut, mut_prob=max(mut_prob, 0.25))

                # Evaluate children, merge, keep top-P
                child_scores = self._score_batch(children); total_evals += int(children.shape[0])

                all_keys = np.vstack([elite_keys, pop, children]).astype(KEY_DTYPE, copy=False)
                all_scores = np.concatenate([scores[:elites], scores, child_scores])

                keep = self._stable_topk_indices(all_scores, int(P))

                pop = np.ascontiguousarray(all_keys[keep], dtype=KEY_DTYPE)
                scores = np.ascontiguousarray(all_scores[keep], dtype=np.float64)

                # Track best and plateau
                if scores[0] > best_score:
                    best_score = float(scores[0])
                    best_key = pop[0].copy()
                plateau_stop = self._early_stop_update(float(best_score), int(gen))
                since_improve = int(self._since_improve(int(gen)))

                # Percent-bucket progress
                self._progress_pct(
                    gen,
                    G,
                    generation=int(gen),
                    pop_size=int(P),
                    best_score=float(best_score),
                    evals=int(total_evals),
                    since_improve=int(since_improve),
                    preview_key=best_key,
                )

                # Unified early stop
                if self._early_stop_stop_score(float(best_score)) or plateau_stop:
                    break

            # Finalise
            if self._stop_reason is None:
                self._stop_reason = "max_generations_reached"
            self._end_span(getattr(self, "_span", None),
                           generations=int(gen),
                           candidates=int(total_evals),
                           best_score=float(best_score),
                           reason=self._stop_reason)
            return self._finalize_solution(best_key, float(best_score))

        except Exception as e:
            self._end_span(getattr(self, "_span", None), error=str(e))
            raise
