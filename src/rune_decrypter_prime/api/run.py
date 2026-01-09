from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from rune_decrypter_prime.core.types import Device, Direction
from rune_decrypter_prime.api.pipeline import execute_run
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.api.normalize import (
    normalize_ciphertext,
    _assert_core_ready,
    normalize_device,
    normalize_optimizer_spec,
    normalize_encoding_dir,
    normalize_scorer_params,
)
from rune_decrypter_prime.api._resolve import resolve_scorer_aliases
from rune_decrypter_prime.core.config import ScoringConfig, SolverConfig


class RunAPI:
    """
    High-level entrypoint for the decrypter.  This class owns the full solve
    pipeline: it normalises user inputs, constructs the cipher and solver
    configuration, seeds the master RNG, and delegates to the execution
    pipeline.  This replaces the legacy ``run.solve`` function; callers
    should prefer :meth:`RunAPI.run` for clarity.
    """

    @classmethod
    def run(
        cls,
        text: Union[str, np.ndarray, List[int], Tuple[np.ndarray, Sequence[Sequence[int]]]],
        *,
        cipher: CipherSpec,
        key: Union[KeySpec, Tuple[KeySpec, KeySpec]],
        solver: SolverSpec,
        device: Optional[Union[str, Device]] = Device.CPU,
        scorer: str = "rune",
        scorer_params: Optional[Dict[str, Any]] = None,
        logging: Optional[Dict[str, Any]] = None,
        wli_data: Optional[Sequence[Sequence[int]]] = None,
        force_no_wli: Optional[bool] = None,
        initial_keys: Optional[List[List[int]]] = None,
        telemetry_on: bool = True,
        encoding_dir: Optional[Union[str, Direction]] = Direction.RTL,
        initial_text_permutation_indices: Optional[Sequence[int]] = None,
        interruptors_exact: Optional[Sequence[int]] = None,
        interruptors_pool: Optional[Sequence[int]] = None,
        interruptors_max: Optional[int] = None,
    ):
        """
        Run a single decrypt attempt over the given ciphertext.

        This method accepts the plaintext/ciphertext in ``text``, along with a
        chosen cipher specification (``cipher``), key plan (``key``), and
        optimiser specification (``solver``).  Additional optional parameters
        configure the device, scoring implementation, logging, word-level
        segmentation (WLI), a pre-seeded key pool, the telemetry flag, the
        text-encoding direction, and an optional input text permutation.

        The method normalises all inputs (e.g. strings to enums, casing),
        applies WLI inference if not provided, resolves scorer aliases and
        parameters, and builds a solver configuration object.  It then
        delegates to :func:`~rune_decrypter_prime.api.pipeline.execute_run`,
        which performs the actual decryption and returns a structured
        solution.
        """
        # Normalise device and encoding direction
        device = normalize_device(device)
        encoding_dir = normalize_encoding_dir(encoding_dir)

        # Normalise ciphertext and optional WLI data
        ct, wli = normalize_ciphertext(text, wli_data)
        if force_no_wli:
            wli = None
        _assert_core_ready(ct, wli)

        # Normalise scorer parameters and build scoring config
        scorer_params = normalize_scorer_params(resolve_scorer_aliases(scorer_params or {}))
        scoring_cfg = ScoringConfig(**scorer_params)
        scoring_cfg.encoding_dir = encoding_dir

        # Normalise optimiser specification and build solver config
        opt = normalize_optimizer_spec({"name": solver.name, **solver.params})
        opt_name = opt.pop("name")
        solver_cfg = SolverConfig(name=opt_name, params=opt, seed=solver.seed)

        # Delegate to the execution pipeline
        return execute_run(
            ciphertext=ct,
            wli=wli,
            cipher=cipher,
            key=key,
            solver=solver_cfg,
            scoring=scoring_cfg,
            scorer_name=scorer,
            logging=logging,
            telemetry_on=telemetry_on,
            device=device,
            encoding_dir=encoding_dir,
            initial_keys=initial_keys,
            initial_text_permutation_indices=initial_text_permutation_indices,
            interruptors_exact=interruptors_exact,
            interruptors_pool=interruptors_pool,
            interruptors_max=interruptors_max,
        )

    # Backwards compatibility: ``solve`` maps to ``run`` for existing code
    solve = run


def run(*args, **kwargs):
    """
    Convenience wrapper around :meth:`RunAPI.run`.  Accepts the same
    parameters as :meth:`RunAPI.run` and returns its result.  This free
    function is provided for ease of use so that callers can write
    ``from rune_decrypter_prime.api.run import run`` and call ``run(...)``
    directly.
    """
    return RunAPI.run(*args, **kwargs)

# Backwards compatibility alias: map legacy ``solve`` to the new ``run``
solve = run
