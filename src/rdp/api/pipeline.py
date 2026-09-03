from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence
from types import SimpleNamespace
import numpy as np

from rdp.core.types import Device, Direction, SolverName, KEY_DTYPE
from rdp.core.config.scoring import ScoringConfig
from rdp.core.config.solver import SolverConfig
from rdp.core.config.logging_config import LoggingConfig, init_logging
from rdp.api.pipeline_helpers import coerce_wli_for_config
from rdp.core.engine.finalization import finalize_solution
from rdp.core.config.cipher import materialize_cipher_config
from rdp.core.types import ComputeDevice, TextDirection

# Stage-2 imports
from rdp.core.problem.spec import ProblemSpec
from rdp.core.problem.instance import ProblemInstance
from rdp.core.engine import EngineConfig, solve as engine_solve
from rdp.api.normalize import normalize_optimizer_name  # str -> SolverName

def execute_run(
    *,
    ciphertext: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    cipher,
    key,
    solver: SolverConfig,
    scoring: ScoringConfig,
    scorer_name: str,
    logging_config: Optional[LoggingConfig],
    logging_runtime: Mapping[str, Any],
    initialize_logging: bool,
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
    if initialize_logging and logging_config is not None:
        init_logging(logging_config)

    # 1) Canonical CipherConfig
    cipher_cfg = materialize_cipher_config(
        cipher=cipher,
        key_space=key,
        ciphertext=ciphertext,
        word_lengths=coerce_wli_for_config(wli),
        compute_device=(ComputeDevice.CUDA if device is Device.CUDA else ComputeDevice.CPU),
        text_direction=(
            TextDirection.RIGHT_TO_LEFT
            if encoding_dir is Direction.RTL
            else TextDirection.LEFT_TO_RIGHT
        ),
        text_permutation=initial_text_permutation_indices,
        initial_keys=initial_keys,
        interruptors=interruptors,
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
    cb = logging_runtime.get("progress_callback")
    if callable(cb):
        progress_cb = cb

    # 3) EngineConfig + run
    solver_kind: SolverName = normalize_optimizer_name(solver.name)
    log_int = 50
    try:
        log_int = int(logging_runtime.get("log_interval", 50))
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
        progress_callback=progress_cb,
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
