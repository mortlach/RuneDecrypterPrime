# -*- coding: utf-8 -*-
"""
solver/beam.py — KeyOps-integrated, configurable Beam Optimiser (telemetry-stable)

Behavioural goals:
  - Defaults match current behaviour (W/2 parents, 1 random position per round, exhaustive children).
  - Uses KeyOps verbs (expand_position / batch_neighbors / mutate) only; no key-type branching.
  - Telemetry schema unchanged; we only enrich params/progress payloads with extra fields.
  - Deterministic: all sampling uses injected rng; cyclic/random position modes are reproducible.
"""

from __future__ import annotations
from typing import Optional
from collections import deque
import numpy as np

from rdp.core.types import SolverName, KEY_DTYPE
from .solver_base import SolverBase


class BeamSolver(SolverBase):
    """
    Beam search over full keys.
      - Start with W keys (seeded or random).
      - For R rounds, expand a subset of parents at a subset of positions.
      - Keep top-W by score.
      - Optionally repeat from independent random populations.
      - Return the best-of-beam.
    """
    name = "beam"

    def __init__(self, problem, opt_cfg=None, **kwargs):
        """
        Accept legacy (problem, opt_cfg) from solver_engine, but call the new base.
        opt_cfg is expected to be a mapping/dotdict with canonical names.
        """
        params = {}
        if opt_cfg is not None:
            if isinstance(opt_cfg, dict):
                params = dict(opt_cfg)
            elif hasattr(opt_cfg, "as_dict"):
                params = dict(opt_cfg.as_dict())
            else:
                params = dict(getattr(opt_cfg, "__dict__", {}))

        # Defaults for beam (stable)
        params.setdefault("beam_width", 16)
        params.setdefault("rounds", 0)  # 0 = auto: max(2*K, 12)
        params.setdefault("restarts", 1)

        # Expansion controls
        params.setdefault("expand.parent_mode", "top")         # "top" | "stochastic" | "diverse"
        params.setdefault("expand.parents_frac", 0.5)
        params.setdefault("expand.parents_cap", None)
        params.setdefault("expand.parent_temp", 1.0)

        params.setdefault("expand.positions_per_round", 1)     # int | "all"
        params.setdefault("expand.position_mode", "random")    # "random" | "cyclic"
        params.setdefault("expand.position_cap", None)

        params.setdefault("expand.max_children_per_parent", None)  # None = exhaustive

        params.setdefault("expand.dedup", True)
        params.setdefault("plateau_rounds", 0)  # 0 = off

        rng = kwargs.get("rng", None)
        if rng is None:
            raise TypeError("BeamSolver requires rng=np.random.Generator from the solver engine")

        super().__init__(
            problem,
            optimizer_name=SolverName.BEAM,
            params=params,
            rng=rng,
            seed_keys=kwargs.get("seed_keys", None),
            stop_score=kwargs.get("stop_score", None),
            verbose=bool(kwargs.get("verbose", True)),
            log_interval=int(kwargs.get("log_interval", 50)),
        )

    # ── Expansion params normalization ──
    def _normalize_expand_params(self):
        p = self.params

        def pick(*names, default=None, cast=float):
            for n in names:
                if n in p and p[n] is not None:
                    try:
                        return cast(p[n])
                    except Exception:
                        pass
            return default

        mode = pick("expand_mode", "expand.mode", "beam.expand_mode",
                    default="sweep", cast=str).lower()
        if mode not in ("sweep", "sample", "exhaustive"):
            mode = "sweep"

        top_parents_factor = pick("top_parents_factor", "expand.top_parents_factor", "beam.top_parents_factor",
                                  default=0.5, cast=float)
        sample_per_parent = pick("sample_per_parent", "expand.sample_per_parent", "beam.sample_per_parent",
                                 default=None, cast=int)
        maximum_children_per_parent = pick(
            "maximum_children_per_parent",
            "expand.max_children_per_parent",
            "beam.maximum_children_per_parent",
            default=None,
            cast=int,
        )

        traits = getattr(self.keyops, "caps", None)
        traits = getattr(traits, "traits", {}) if traits else {}
        A = int(traits.get("mod", 0)) or 0  # 0 if unknown (e.g., permutation family)

        return {
            "mode": mode,
            "top_parents_factor": float(top_parents_factor),
            "sample_per_parent": None if sample_per_parent is None else int(sample_per_parent),
            "maximum_children_per_parent": (
                None
                if maximum_children_per_parent is None
                else max(1, int(maximum_children_per_parent))
            ),
            "alphabet": A,
        }

    # ── Build expanded candidate batch for one round; never return empty ──
    def _expand_round_safe(self, beam: np.ndarray, scores: np.ndarray, round_idx: int):
        """
        Returns (expanded, attempted, parents_used, cands_per_parent)
        and guarantees expanded.shape[0] >= 1 by falling back to neighbors/mutate.
        """
        K = self.K
        cfg = self._normalize_expand_params()
        mode = cfg["mode"]
        A = cfg["alphabet"]
        maximum_children_per_parent = cfg["maximum_children_per_parent"]

        def _cap_children(children: np.ndarray) -> np.ndarray:
            if (
                maximum_children_per_parent is None
                or children.shape[0] <= maximum_children_per_parent
            ):
                return children
            selected = self.rng.choice(
                children.shape[0],
                size=maximum_children_per_parent,
                replace=False,
            )
            return children[np.sort(selected)]

        # how many parents
        W = int(beam.shape[0])
        parents = max(1, int(W * max(0.0, cfg["top_parents_factor"])))

        # choose parents: top by score
        parent_idx = np.argsort(scores)[-parents:][::-1]
        parent_keys = beam[parent_idx]

        expanded = None
        cands_per_parent = 0

        # Preferred path: expand_position if available (vector keys)
        if "expand_position" in self.keyops.caps.ops:
            if mode == "sweep":
                pos = int((round_idx - 1) % K)  # 1-based round_idx; sweep 0..K-1
                expanded_list = [
                    _cap_children(self.keyops.expand_position(k, pos, self.rng))
                    for k in parent_keys
                ]
                cands_per_parent = int(expanded_list[0].shape[0])
                expanded = np.concatenate(expanded_list, axis=0)

            elif mode == "exhaustive":
                per_parent = []
                cands_per_parent = 0
                for k in parent_keys:
                    cols = [self.keyops.expand_position(k, pos, self.rng) for pos in range(K)]
                    per_parent.append(_cap_children(np.concatenate(cols, axis=0)))
                    cands_per_parent = per_parent[-1].shape[0]
                expanded = np.concatenate(per_parent, axis=0)

            else:  # 'sample'
                pos_vec = self.rng.integers(0, K, size=parents)
                spp = cfg["sample_per_parent"]
                if spp is None:
                    spp = min(A if A > 0 else K, 16)
                if maximum_children_per_parent is not None:
                    spp = min(spp, maximum_children_per_parent)
                spp = max(1, int(spp))
                cands_per_parent = spp
                parts = []
                for k, pos in zip(parent_keys, pos_vec):
                    full = self.keyops.expand_position(k, int(pos), self.rng)  # [A_or_K, K]
                    if full.shape[0] > spp:
                        sel = self.rng.choice(full.shape[0], size=spp, replace=False)
                        full = full[sel]
                    parts.append(full)
                expanded = np.concatenate(parts, axis=0)

        # Fallbacks if expand_position missing or produced empty
        if expanded is None or expanded.size == 0:
            if "batch_neighbors" in self.keyops.caps.ops:
                neigh = [
                    _cap_children(self.keyops.batch_neighbors(k, max(2, K), self.rng))
                    for k in beam
                ]
                expanded = np.concatenate(neigh, axis=0)
                parents = int(beam.shape[0])
                cands_per_parent = int(expanded.shape[0] // max(1, parents))
            else:
                expanded = np.vstack([self.keyops.mutate(k, self.rng) for k in beam]).astype(KEY_DTYPE)
                parents = int(beam.shape[0])
                cands_per_parent = 1

        attempted = int(expanded.shape[0])
        if attempted <= 0:
            # Hard safety: create at least one by mutating the best key
            k_best = beam[int(np.argmax(scores))]
            expanded = self.keyops.mutate(k_best, self.rng).reshape(1, -1).astype(KEY_DTYPE)
            attempted = 1
            parents = 1
            cands_per_parent = 1

        expanded = np.ascontiguousarray(expanded, dtype=KEY_DTYPE)
        return expanded, attempted, int(parents), int(cands_per_parent)

    # -------------------------- main solve ---------------------------

    def solve(self):
        # Resolve primary params BEFORE starting the span so start-event shows the real values
        W: int = int(self.get_param("beam_width", 16))
        restarts: int = max(1, int(self.get_param("restarts", 1)))
        rounds_cfg: int = int(self.get_param("rounds", 0))
        rounds: int = rounds_cfg if rounds_cfg > 0 else max(2 * self.K, 12)

        # Expansion config (resolved)
        p_mode: str = str(self.get_param("expand.parent_mode", "random")).lower()
        parents_frac: float = float(self.get_param("expand.parents_frac", 0.5))
        parents_cap_raw = self.get_param("expand.parents_cap", None)
        parents_cap: Optional[int] = None if parents_cap_raw in (None, 0) else int(parents_cap_raw)
        parent_temp: float = float(self.get_param("expand.parent_temp", 1.0))

        pos_per_round_raw = self.get_param("expand.positions_per_round", 1)
        pos_mode: str = str(self.get_param("expand.position_mode", "random")).lower()
        pos_cap_raw = self.get_param("expand.position_cap", None)
        pos_cap: Optional[int] = None if pos_cap_raw in (None, 0) else int(pos_cap_raw)

        m_children_raw = self.get_param("expand.max_children_per_parent", None)
        max_children: Optional[int] = None if m_children_raw in (None, 0) else int(m_children_raw)

        dedup_on: bool = bool(self.get_param("expand.dedup", True))
        plateau_rounds: int = int(self.get_param("plateau_rounds", 0))

        # Parents count per round
        parents_base = max(1, int(np.floor(parents_frac * W)))
        parents_k = min(parents_cap, parents_base) if parents_cap else parents_base

        fast = self._maybe_return_test_key_fastpath(SolverName.BEAM)
        if fast is not None:
            return fast

        # Positions per round
        if isinstance(pos_per_round_raw, str) and pos_per_round_raw.lower() == "all":
            pos_per_round: int = self.K if pos_cap is None else min(self.K, pos_cap)
            pos_all = True
        else:
            pos_per_round = max(1, int(pos_per_round_raw))
            pos_all = False

        # Snapshot resolved params so telemetry_start prints what actually runs
        self.params["beam_width"] = W
        self.params["restarts"] = restarts
        self.params["rounds"] = rounds
        self.params["expand.parent_mode"] = p_mode
        self.params["expand.parents"] = parents_k
        self.params["expand.parent_temp"] = parent_temp
        self.params["expand.positions_per_round"] = ("all" if pos_all else pos_per_round)
        self.params["expand.position_mode"] = pos_mode
        self.params["expand.max_children_per_parent"] = max_children
        self.params["expand.dedup"] = dedup_on
        self.params["plateau_rounds"] = plateau_rounds

        span = self._start_span()
        candidates_seen = 0

        try:
            best_key = None
            best_score = float("-inf")
            best_beam = None
            selected_restart = 0
            restart_scores: list[float] = []
            completed_rounds = 0
            final_reason = "max_rounds_reached"

            for restart in range(restarts):
                # Dedup is deliberately restart-local so an independent start can
                # revisit candidates seen by an earlier population.
                recent_hashes: set[bytes] = set()
                recent_queue: deque[bytes] = deque()
                dedup_window = max(1, 4 * W)

                def _dedup_rows(u8: np.ndarray) -> np.ndarray:
                    if not dedup_on or u8.size == 0:
                        return u8
                    keep = []
                    for row in u8:
                        b = row.tobytes()
                        if b in recent_hashes:
                            continue
                        keep.append(row)
                        recent_hashes.add(b)
                        recent_queue.append(b)
                        if len(recent_queue) > dedup_window:
                            old = recent_queue.popleft()
                            recent_hashes.discard(old)
                    if not keep:
                        return u8[:0]
                    return np.ascontiguousarray(np.vstack(keep), dtype=KEY_DTYPE)

                self._maybe_update_hamming_progress(0.0)
                if restart == 0 and self.seed_keys is not None and len(self.seed_keys) > 0:
                    beam = np.ascontiguousarray(self.seed_keys, dtype=KEY_DTYPE)
                    if beam.shape[0] < W:
                        extra_n = W - beam.shape[0]
                        extra = (self.keyops.make_population(extra_n, self.rng)
                                 if "make_population" in self.keyops.caps.ops
                                 else np.vstack([self.keyops.random(self.rng) for _ in range(extra_n)]).astype(KEY_DTYPE))
                        beam = np.ascontiguousarray(np.vstack([beam, extra]), dtype=KEY_DTYPE)
                    else:
                        beam = np.ascontiguousarray(beam[:W], dtype=KEY_DTYPE)
                else:
                    beam = (self.keyops.make_population(W, self.rng)
                            if "make_population" in self.keyops.caps.ops
                            else np.vstack([self.keyops.random(self.rng) for _ in range(W)]).astype(KEY_DTYPE))

                scores = self._score_batch(beam)
                candidates_seen += int(beam.shape[0])
                self._early_stop_reset(
                    initial_best=float(np.max(scores)),
                    plateau_override=int(self.get_param("plateau_rounds", 0)),
                )

                for r in range(1, rounds + 1):
                    completed_rounds += 1
                    self._maybe_update_hamming_progress(r / float(rounds))
                    expanded, attempted, parents_used, cpp = self._expand_round_safe(beam, scores, r)
                    if dedup_on:
                        expanded = _dedup_rows(expanded)

                    exp_scores = self._score_batch(expanded)
                    candidates_seen += int(expanded.shape[0])
                    all_keys = np.vstack([beam, expanded]).astype(KEY_DTYPE, copy=False)
                    all_scores = np.concatenate([scores, exp_scores])
                    idx = self._stable_topk_indices(all_scores, int(W))
                    beam = np.ascontiguousarray(all_keys[idx], dtype=KEY_DTYPE)
                    scores = np.ascontiguousarray(all_scores[idx], dtype=np.float64)

                    progress_step = restart * rounds + r
                    self._progress_pct(
                        progress_step,
                        rounds * restarts,
                        best_score=float(scores[0]),
                        restart=int(restart),
                        restarts=int(restarts),
                        round=int(r),
                        rounds=int(rounds),
                        attempted=int(attempted),
                        kept=int(beam.shape[0]),
                        parents=int(parents_used),
                        cands_per_parent=int(cpp),
                        preview_key=beam[0] if beam.size else None,
                    )

                    round_best = float(scores[0])
                    if self._early_stop_stop_score(round_best) or self._early_stop_update(round_best, r):
                        break

                restart_best_idx = int(np.argmax(scores))
                restart_best_score = float(scores[restart_best_idx])
                restart_reason = self._stop_reason or "max_rounds_reached"
                restart_scores.append(restart_best_score)
                if best_key is None or restart_best_score > best_score:
                    best_key = beam[restart_best_idx].copy()
                    best_score = restart_best_score
                    best_beam = beam.copy()
                    selected_restart = restart

                final_reason = restart_reason
                if restart_reason == "target_score":
                    break

            if best_key is None:
                raise RuntimeError("beam search completed without a candidate")
            self._stop_reason = final_reason
            self._end_span(
                span,
                candidates=int(candidates_seen),
                rounds=int(completed_rounds),
                restarts=int(len(restart_scores)),
                reason=self._stop_reason,
            )
            sol = self._finalize_solution(best_key, best_score)

            # Opportunistic: expose final beam keys for Hybrid GA seeding ([W,K] uint8).
            try:
                if isinstance(best_beam, np.ndarray) and best_beam.ndim == 2 and best_beam.shape[1] == self.K:
                    meta = getattr(sol, "meta", None)
                    if isinstance(meta, dict):
                        beam_meta = meta.setdefault("beam", {})
                        beam_meta["final_keys"] = best_beam.astype(KEY_DTYPE, copy=True).tolist()
                        beam_meta["restarts"] = int(len(restart_scores))
                        beam_meta["selected_restart"] = int(selected_restart)
                        beam_meta["restart_scores"] = list(restart_scores)
            except Exception:
                pass
            return sol

        except Exception as e:
            self._end_span(span, error=str(e))
            raise
