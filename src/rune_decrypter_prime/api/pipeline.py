from __future__ import annotations
from typing import Any, Dict, Optional, Sequence
from types import SimpleNamespace
import numpy as np

from rune_decrypter_prime.core.types import Device, Direction, SolverName, KEY_DTYPE
from rune_decrypter_prime.api.fastpaths import maybe_known_key_fastpath
from rune_decrypter_prime.api.pipeline_helpers import finalize_solution, coerce_wli_for_config
from rune_decrypter_prime.api.wrappers.registry import build_cipher_config

# Stage-2 imports
from rune_decrypter_prime.core.problem import ProblemSpec, ProblemInstance
from rune_decrypter_prime.core.engine import EngineConfig, solve as engine_solve
from rune_decrypter_prime.api.normalize import normalize_optimizer_name  # str -> SolverName

def execute_run(
    *,
    ciphertext: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    cipher,
    key,
    solver,   # SolverConfig-like
    scoring,  # ScoringConfig-like
    scorer_name: str,
    logging: Optional[Dict[str, Any]],
    telemetry_on: bool,
    device: Device,
    encoding_dir: Direction,
    initial_keys: Optional[Sequence[Sequence[int]]],
    initial_text_permutation_indices: Optional[Sequence[int]],
    interruptors: Optional[Any],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
):
    # 0) Known-key fast path
    fast = maybe_known_key_fastpath(
        cipher=cipher,
        key=key,
        ciphertext=ciphertext,
        wli=wli,
        device=device,
        scoring=scoring,
        scorer_name=scorer_name,
        logging=logging,
        encoding_dir=encoding_dir,
        telemetry_on=telemetry_on,
    )
    if fast is not None:
        return fast

    # 1) Canonical CipherConfig
    cipher_cfg = build_cipher_config(
        cipher=cipher,
        key=key,
        ciphertext=ciphertext,
        wli=coerce_wli_for_config(wli),
        device=device,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=initial_text_permutation_indices,
        initial_keys=initial_keys,
        interruptors=interruptors,
        interruptors_exact=interruptors_exact,
        interruptors_pool=interruptors_pool,
        interruptors_max=interruptors_max,
    )

    # 2) Materialise Stage-2 ProblemInstance
    spec = ProblemSpec(
        text="",
        text_encoding_direction=encoding_dir,
        cipher_cfg=cipher_cfg,
        scorer_params=scoring,
        input_permutation=initial_text_permutation_indices,
    )
    instance = ProblemInstance.materialise(spec)

    progress_cb = None
    if isinstance(logging, dict):
        cb = logging.get("progress_callback")
        if callable(cb):
            progress_cb = cb
    if progress_cb is not None:
        tele = getattr(instance.problem, "telemetry", None)
        if tele is None:
            tele = {}
            instance.problem.telemetry = tele
        try:
            tele["progress_callback"] = progress_cb
        except Exception:
            pass

    # 3) EngineConfig + run
    solver_kind: SolverName = normalize_optimizer_name(solver.name)
    log_int = 50
    if isinstance(logging, dict):
        try:
            log_int = int(logging.get("log_interval", 50))
        except Exception:
            pass

    # Ensure a deterministic default when seed is not supplied
    effective_seed = getattr(solver, "seed", None)
    if effective_seed is None:
        effective_seed = 0

    eng_cfg = EngineConfig(
        solver=solver_kind,
        params=dict(getattr(solver, "params", {}) or {}),
        seed=effective_seed,
        stop_score=None,
        verbose=True,
        log_interval=log_int,
        seed_keys=(np.asarray(initial_keys, dtype=KEY_DTYPE) if initial_keys is not None else None),
    )

    result = engine_solve(instance, eng_cfg)

    # 4) Finalise outward-facing Solution
    compat_cfg = SimpleNamespace(cipher=cipher_cfg, scorer_params=scoring, solver=solver)
    return finalize_solution(
        instance.problem,
        result,
        ciphertext=ciphertext,
        wli=wli,
        cipher=cipher,
        encoding_dir=encoding_dir,
        cfg=compat_cfg,
        telemetry_on=telemetry_on,
        pipeline_block=instance.pipeline_block,
    )
