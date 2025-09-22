# ============================================================
# rune_decrypter_prime/optimizers/beam_optimizer.py
#   Beam search (device-agnostic, TelemetrySpan)
# ============================================================

from __future__ import annotations

from typing import List, Optional
import numpy as np

from rune_decrypter_prime.core.config import Solution, OptimizerConfig
from rune_decrypter_prime.core.problem import DecryptionProblem
from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
from rune_decrypter_prime.core.telemetry_helpers import (
    TelemetrySpan,
    attach_telemetry_to_meta,
)
from rune_decrypter_prime.utils.runeglish import Runeglish


class BeamSearchOptimizer(OptimizerBase):
    """
    Deterministic beam search over base-A keys (A comes from the cipher).

    Design:
      • Device-agnostic: all scoring routes through `problem.evaluate_keys(keys_2d)`
        (the problem/scorer pick CPU vs Torch/CUDA). The optimizer stays in NumPy.
      • Partial heuristic: for a depth d prefix, consider absolute positions i
        whose column (i % K) < d+1; subtract the known prefix symbols at those
        columns and score the resulting plaintext slice.
      • Full depth: evaluate all candidate keys via batch scorer and pick the top W.

    Telemetry:
      Uses TelemetrySpan to emit:
        - optimizer_start
        - optimizer_progress (per depth)
        - optimizer_end (with elapsed and rollups)
      `attach_telemetry_to_meta()` injects finalized telemetry into the Solution meta.

    Public API (aligned with GA/SA):
      __init__(problem, opt_cfg)
      search() -> Solution(key: List[int], plaintext: str, score: float, meta: dict)

    Parameters read from OptimizerConfig.params:
      beam_width: int = 64
      stop_score: Optional[float] = None
      verbose   : bool = False
      test_key  : Optional[List[int]] (fast path used via base helper)
    """

    # -------------- init & setup ---------------------
    def __init__(self, problem: DecryptionProblem, opt_cfg: OptimizerConfig):
        super().__init__(problem, opt_cfg)

        # ----- parameters -----
        self.W = int(self.get_param("beam_width", 64))
        self.stop_score = self.get_param("stop_score", None)
        self.verbose = bool(self.get_param("verbose", False))

        # ----- cipher/problem-derived -----
        self.A = int(getattr(getattr(problem, "cipher", None), "A", 29))

        # Precompute absolute column indices and per-depth index lists
        L = int(self._ct.size)
        self._cols = (np.arange(L, dtype=np.int64) % self.K)  # 0..K-1 per position
        # depth d (0-based) corresponds to prefix length d+1
        self._depth_idx: List[np.ndarray] = [
            np.where(self._cols < (d + 1))[0] for d in range(self.K)
        ]

        # Alphabet symbols used during expansion
        self._symbols = np.arange(self.A, dtype=np.uint8)

        # Optional future hooks (kept for parity with other optimizers)
        self._interrupt_idx: Optional[np.ndarray] = None
        self._intr_pool: Optional[np.ndarray] = None
        self._intr_max: Optional[int] = None
        self._t_modes = None

        if self.verbose:
            print(f"▶ Beam search initialized: K={self.K}, width={self.W}, A={self.A}")

    # -------------- optional engine hooks -----------
    def set_interrupt_idx(self, idx: np.ndarray | None):
        self._interrupt_idx = None if idx is None else np.asarray(idx, np.intp)

    def set_interrupt_search_space(self, pool, max_count):
        self._intr_pool = None if pool is None else np.asarray(pool, np.intp)
        self._intr_max = None if max_count is None else int(max_count)

    def set_transposition_modes(self, modes):
        self._t_modes = modes  # stored for future use / parity

    # -------------- helpers -------------------------
    @staticmethod
    def _as_numpy(x) -> np.ndarray:
        """Best-effort conversion to NumPy (handles torch/cupy scalars/arrays)."""
        try:
            if hasattr(x, "detach") and hasattr(x, "cpu") and hasattr(x, "numpy"):
                return x.detach().cpu().numpy()
            if hasattr(x, "get"):  # CuPy
                import numpy as _np
                return _np.asarray(x.get())
        except Exception:
            pass
        import numpy as _np
        return _np.asarray(x)

    def _score_full_scalar(self, key_idx: np.ndarray) -> float:
        """
        Score a single key by routing through the problem's batch scorer.
        Returns a Python float.
        """
        key_row = np.asarray(key_idx, dtype=np.uint8)[None, :]  # [1,K]
        out = self.problem.evaluate_keys(key_row)
        arr = self._as_numpy(out)
        return float(arr[0])

    def _score_batch_full(self, keys_2d: np.ndarray) -> np.ndarray:
        """
        Score a batch of keys. Returns float32 NumPy array, shape [M].
        """
        keys_2d = np.asarray(keys_2d, dtype=np.uint8, order="C")
        out = self.problem.evaluate_keys(keys_2d)
        return self._as_numpy(out).astype(np.float32, copy=False)

    def _partial_score(self, key_prefix: np.ndarray, depth: int) -> float:
        """
        Partial heuristic score for a prefix of length (depth+1).

        Logic:
          - Consider absolute positions i with (i % K) < depth+1
          - Decrypt those positions using the available prefix
          - Score the resulting plaintext slice with the scalar scorer

        Returns a Python float.
        """
        idx = self._depth_idx[depth]  # absolute positions with (i % K) < depth+1
        if idx.size == 0:
            return -1e-9

        p = np.asarray(key_prefix, dtype=np.uint8)
        prefix_len = int(p.size)
        if prefix_len != (depth + 1):
            return -1e-9  # contract guard

        cols = self._cols[idx]  # values in 0..K-1, guaranteed < prefix_len here
        ct_sel = self._ct[idx].astype(np.int16)
        k_sel = p[cols].astype(np.int16)

        pt_slice = ((ct_sel - k_sel) % self.A).astype(np.int8)
        wli_slice = self._wli[idx]
        s = self.problem.scorer.score(pt_slice, wli_slice)
        arr = self._as_numpy(s)
        return float(arr if np.isscalar(arr) else arr.item())

    # -------------- main search ---------------------
    def search(self) -> Solution:
        """
        Run a deterministic beam search to recover the Vigenère key and plaintext.

        Contract
        --------
        • Determinism: governed by upstream RNG seeding; search logic is pure.
        • Telemetry: uses TelemetrySpan; writes progress per depth and finalizes
          with span.end(pruned_total, best_score) BEFORE attaching telemetry into
          the result meta (so elapsed_sec & rollups are present).
        • Device policy & scoring dtype are governed by the scorer injected via
          the Problem; this function does not read env/CLI flags.

        Returns
        -------
        Solution(key: List[int], plaintext: str, score: float, meta: Dict[str, Any])
        """
        # --- Fast path for smoke tests / known-key validation --------------------
        fast = self._maybe_return_test_key_fastpath("beam")
        if fast is not None:
            return fast

        # --- Telemetry span setup ------------------------------------------------
        params_for_span = {"beam_width": int(self.W), "K": int(self.K)}
        pruned_total = 0

        # --- Main search loop ----------------------------------------------------
        with TelemetrySpan(self.problem, "beam", params_for_span) as span:
            # Initialize beam with an empty prefix and a sentinel score.
            beam_keys: List[np.ndarray] = [np.empty(0, dtype=np.uint8)]
            beam_scores: List[float] = [-1e-9]

            # Depth expands from 0..K-1 (prefix length = depth+1)
            for depth in range(self.K):
                candidate_keys: List[np.ndarray] = []

                # Expand each current prefix by all symbols.
                for prefix in beam_keys:
                    if prefix.size != depth:
                        continue
                    base = prefix
                    # Append each symbol; keep as contiguous uint8
                    candidate_keys.extend(
                        [np.append(base, sym).astype(np.uint8) for sym in self._symbols]
                    )

                if not candidate_keys:
                    break

                # Score candidates: heuristic for partial, full scorer at final depth.
                if depth + 1 == self.K:
                    cand_mat = np.vstack(candidate_keys)  # [M, K]
                    candidate_scores = self._score_batch_full(cand_mat)  # [M]
                else:
                    candidate_scores = np.asarray(
                        [self._partial_score(kp, depth) for kp in candidate_keys],
                        dtype=np.float32,
                    )

                # Keep the top W.
                if candidate_scores.size > self.W:
                    top = np.argpartition(candidate_scores, -self.W)[-self.W:]
                    order = top[np.argsort(candidate_scores[top])]
                    beam_keys = [candidate_keys[i] for i in order]
                    beam_scores = [float(candidate_scores[i]) for i in order]
                else:
                    beam_keys = candidate_keys
                    beam_scores = [float(s) for s in candidate_scores]

                # Progress accounting for telemetry.
                attempted = len(candidate_keys)
                kept = len(beam_keys)
                pruned = max(0, attempted - kept)
                pruned_total += pruned
                top_score = float(
                    np.max(np.asarray(beam_scores, dtype=np.float32))
                ) if kept else float("-inf")

                span.progress(
                    depth=int(depth + 1),
                    attempted=int(attempted),
                    kept=int(kept),
                    pruned=int(pruned),
                    top=float(top_score),
                )

                # Optional early stop on score threshold.
                if self.stop_score is not None and top_score >= float(self.stop_score):
                    if self.verbose:
                        print(f"[Beam] early-stop at depth {depth + 1}: best ≥ {self.stop_score}")
                    break

                if self.verbose:
                    top3 = [round(s, 4) for s in sorted(beam_scores)[-3:]]
                    print(f"[Beam {depth + 1}/{self.K}] top candidates: {top3}")

            # Select the best candidate from the final beam.
            beam_scores_np = np.asarray(beam_scores, dtype=np.float32)
            best_idx = int(np.argmax(beam_scores_np))
            best_key = beam_keys[best_idx]
            best_score = float(beam_scores_np[best_idx])

            # Final decrypt with the best key.
            pt_idx = self.problem.cipher.decrypt(key=best_key, ciphertext=self._ct)[0]
            pt_str = Runeglish.to_rune(pt_idx, self._wli)

            # IMPORTANT: close span BEFORE attaching telemetry, so elapsed_sec & rollups are present.
            span.end(pruned_total=int(pruned_total), best_score=float(best_score))

        # Attach finalized telemetry after span.end().
        from rune_decrypter_prime.utils.telemetry import stash as _tstash
        meta = {"optimizer": "beam", "interrupt_idx": []}
        meta = attach_telemetry_to_meta(self.problem, meta)

        return Solution(best_key.tolist(), pt_str, float(best_score), meta)
