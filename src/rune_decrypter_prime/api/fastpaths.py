from __future__ import annotations

from typing import Any, Dict, Optional, Sequence
import numpy as np

from types import SimpleNamespace

from rune_decrypter_prime.api.pipeline_helpers import finalize_solution, coerce_wli_for_config
from rune_decrypter_prime.core.config import CipherConfig, SolverConfig
from rune_decrypter_prime.core.types import Direction, SolverName
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
from rune_decrypter_prime.telemetry.pipeline import make_pipeline_block


def maybe_known_key_fastpath(
    *,
    cipher: CipherSpec,
    key: KeySpec,
    ciphertext: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    device,
    scoring,
    scorer_name: str,
    logging: Optional[Dict[str, Any]],
    encoding_dir: Direction,
    telemetry_on: bool,
):
    if not isinstance(key, KeySpec) or key.plan not in ("otp", "const"):
        return None

    L = int(ciphertext.size)
    if key.plan == "otp":
        stream = key.params.get("stream")
        if stream is None:
            raise ValueError("OTP KeySpec requires 'stream' parameter.")
        k = np.asarray(stream, dtype=np.uint8).reshape(-1)
    else:
        val = int(key.params.get("value", 0))
        k = np.full(L, val, dtype=np.uint8)
    if k.size < L:
        k = np.resize(k, L)
    elif k.size > L:
        k = k[:L]

    cfg_cipher = CipherConfig(
        ciphertext=ciphertext,
        wli_data=coerce_wli_for_config(wli),
        key_length=int(k.size),
        encoding_dir=encoding_dir,
        device=device,
        name=(cipher.name or cipher.kind),
    )
    setattr(cfg_cipher, "text_transposition", "ltr")
    setattr(cfg_cipher, "spec", cipher)

    cfg_opt = SolverConfig(name="beam", params={"beam_width": 1, "test_key": k.tolist()})

    from rune_decrypter_prime.core.problem import ProblemSpec, ProblemInstance
    from rune_decrypter_prime.core.engine import EngineConfig, solve as engine_solve

    spec = ProblemSpec(
        text="",
        text_encoding_direction=encoding_dir,
        cipher_cfg=cfg_cipher,
        scorer_params=scoring,
        input_permutation=getattr(cfg_cipher, "initial_text_permutation_indices", None),
    )
    instance = ProblemInstance.materialise(spec)

    log_interval = 50
    if isinstance(logging, dict):
        try:
            log_interval = int(logging.get("log_interval", log_interval))
        except Exception:
            pass

    eng_cfg = EngineConfig(
        solver=SolverName.BEAM,
        params={"beam_width": 1, "test_key": k.tolist()},
        seed=None,
        stop_score=None,
        verbose=True,
        log_interval=log_interval,
    )

    result = engine_solve(instance, eng_cfg)
    compat_solver = SolverConfig(name="beam", params={"beam_width": 1, "test_key": k.tolist()})
    compat_cfg = SimpleNamespace(cipher=cfg_cipher, scorer_params=scoring, solver=compat_solver)

    pipeline_block = instance.pipeline_block
    return finalize_solution(
        instance.problem,
        result,
        ciphertext=ciphertext,
        wli=wli,
        cipher=cipher,
        encoding_dir=encoding_dir,
        cfg=compat_cfg,
        telemetry_on=bool(telemetry_on),
        pipeline_block=pipeline_block,
    )
