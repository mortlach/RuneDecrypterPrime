# ============================================================
# rune_decrypter_prime/core/problem/instance.py
# Runtime materialisation of a Problem from a ProblemSpec.
# ============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


from rune_decrypter_prime.core.problem.spec import ProblemSpec
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.engine.builders import build_cipher, build_scorer
from rune_decrypter_prime.telemetry.pipeline import make_pipeline_block
from rune_decrypter_prime.core.types import Direction, ensure_direction


def _expected_runtime_identity(spec: object) -> str | None:
    from rdp.api.specs import CipherSpec
    from rune_decrypter_prime.core.types import CipherKind, RuntimeCipherKind

    if not isinstance(spec, CipherSpec):
        return None
    if spec.kind in {
        CipherKind.TWO_PERIOD_VIGENERE,
        CipherKind.PERIODIC_WITH_FIXED_STREAM,
        CipherKind.PERIODIC_WITH_PRIME_STREAM,
        CipherKind.TWO_PERIOD_STREAMS,
    }:
        return "scheduled_stream_lookup"
    if spec.kind in {RuntimeCipherKind.USER_MAP2, RuntimeCipherKind.LOOKUP}:
        return "generic_map"
    return spec.kind.value


def _indices_from_perm(perm: Optional[Sequence[int]], n: int) -> Optional[List[int]]:
    if perm is None:
        return None
    idx = [int(x) for x in perm]
    if len(idx) != n:
        raise ValueError(f"input_permutation must have length {n}, got {len(idx)}")
    return idx


@dataclass(slots=True)
class ProblemInstance:
    """
    Fully materialised engine input:
      - cipher/scorer objects
      - DecryptionProblem bound to configs
      - pipeline/telemetry snapshot (for start/end events)
    """

    spec: ProblemSpec
    problem: DecryptionProblem
    pipeline_block: Dict[str, Any]

    # Convenience mirrors for solvers
    K: int
    ciphertext_len: int

    @classmethod
    def materialise(cls, spec: ProblemSpec) -> "ProblemInstance":
        # 1) Build cipher/scorer using existing, tested builders
        cipher = build_cipher(spec.cipher_cfg)
        expected_identity = _expected_runtime_identity(spec.cipher_cfg.spec)
        if expected_identity is not None and spec.cipher_cfg.name != expected_identity:
            raise RuntimeError(
                "runtime cipher identity does not match the typed cipher materialization"
            )
        scorer = build_scorer(spec.cipher_cfg, spec.scorer_params)

        # 2) Bind into the canonical DecryptionProblem
        problem = DecryptionProblem(
            cipher=cipher,
            scorer=scorer,
            c_cfg=spec.cipher_cfg,
            s_cfg=spec.scorer_params,
        )

        # Enforce direction for the pipeline block
        direction: Direction = ensure_direction(spec.text_encoding_direction)

        # Ciphertext length – prefer problem introspection
        try:
            n = int(
                getattr(problem, "ciphertext_len", 0)
                or getattr(problem, "N_tokens", 0)
                or 0
            )
        except Exception:
            n = 0

        # 3) Build a minimal, stable pipeline snapshot
        perm_indices = (
            _indices_from_perm(spec.input_permutation, n)
            if spec.input_permutation is not None
            else None
        )
        # Ensure WLI schema: list of (int, int) pairs or None
        wli = spec.cipher_cfg.wli_data
        if wli is not None:
            if not (
                isinstance(wli, (list, tuple))
                and all(
                    isinstance(p, (list, tuple))
                    and len(p) == 2
                    and isinstance(p[0], int)
                    and isinstance(p[1], int)
                    for p in wli
                )
            ):
                raise TypeError("WLI must be a list of (int,int) pairs")

        pipeline_block = make_pipeline_block(
            text_encoding_direction=direction,
            ciphertext_len=n,
            text_permutation=perm_indices,
        )

        return cls(
            spec=spec,
            problem=problem,
            pipeline_block=pipeline_block,
            K=int(
                getattr(problem, "K", 0)
                or getattr(problem.keyops.caps, "length", 0)
                or 0
            ),
            ciphertext_len=n,
        )
