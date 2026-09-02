from __future__ import annotations

import importlib

import numpy as np

import rdp.api.pipeline
from rdp import api
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.solver import SolverConfig
from rdp.core.types import Device, Direction


def _minimal_cipher_config() -> CipherConfig:
    return CipherConfig(
        ciphertext=np.asarray([0], dtype=np.uint8),
        wli_data=None,
        key_length=1,
        name="vigenere",
        device=Device.CPU,
        encoding_dir=Direction.RTL,
    )


def test_run_uses_public_defaults_and_always_returns_run_result(monkeypatch) -> None:
    captured: dict[str, object] = {}
    run_module = importlib.import_module("rdp.api.run")
    monkeypatch.setattr(run_module, "execute_run", lambda **kwargs: captured.update(kwargs))

    result = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(indices=(0,)),
            cipher=api.CipherSpec.vigenere(),
            key_space=api.KeySpec.repeating(length=1),
            solver=api.SolverSpec.beam_search(width=1, rounds=0),
            telemetry_enabled=False,
        )
    )

    assert isinstance(result, api.RunResult)
    assert captured["encoding_dir"] is Direction.RTL
    assert captured["device"] is Device.CPU


def test_execute_run_uses_effective_seed_zero(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_instance = type(
        "FakeInstance",
        (),
        {"problem": type("FakeProblem", (), {"telemetry": None})(), "pipeline_block": "pipeline"},
    )()
    monkeypatch.setattr(
        rdp.api.pipeline,
        "materialize_cipher_config",
        lambda **_kwargs: _minimal_cipher_config(),
    )
    monkeypatch.setattr(
        rdp.api.pipeline.ProblemInstance,
        "materialise",
        staticmethod(lambda _spec: fake_instance),
    )

    def fake_engine_solve(_instance, config):
        captured["seed"] = config.seed
        return "engine-result"

    monkeypatch.setattr(rdp.api.pipeline, "engine_solve", fake_engine_solve)
    monkeypatch.setattr(
        rdp.api.pipeline,
        "finalize_solution",
        lambda _problem, result, **_kwargs: result,
    )
    result = rdp.api.pipeline.execute_run(
        ciphertext=np.array([0], dtype=np.uint8),
        wli=None,
        cipher=api.CipherSpec.vigenere(),
        key=api.KeySpec.repeating(length=1),
        solver=SolverConfig(name="beam", params={}, seed=None),
        scoring=api.ScoringConfig(),
        scorer_name="rune",
        logging_config=None,
        logging_runtime={},
        initialize_logging=False,
        telemetry_on=False,
        device=Device.CPU,
        encoding_dir=Direction.RTL,
        initial_keys=None,
        initial_text_permutation_indices=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )

    assert result == "engine-result"
    assert captured["seed"] == 0
