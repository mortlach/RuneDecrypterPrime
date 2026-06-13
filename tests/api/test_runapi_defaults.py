from __future__ import annotations

import importlib
from types import SimpleNamespace

import numpy as np

from rune_decrypter_prime.api import CipherSpec, Direction, KeySpec, RunAPI, SolverSpec
from rune_decrypter_prime.api import fastpaths, pipeline


def test_runapi_omitted_encoding_dir_uses_public_rtl_default(monkeypatch):
    captured = {}

    def fake_execute_run(**kwargs):
        captured.update(kwargs)
        return "ok"

    run_module = importlib.import_module("rune_decrypter_prime.api.run")
    monkeypatch.setattr(run_module, "execute_run", fake_execute_run)

    result = RunAPI.run(
        text=[0],
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.repeat(len=1),
        solver=SolverSpec.beam(beam_width=1, seed=1),
        telemetry_on=False,
    )

    assert result == "ok"
    assert captured["encoding_dir"] is Direction.RTL
    assert captured["scoring"].encoding_dir is Direction.RTL


def test_execute_run_omitted_ordinary_solver_seed_uses_effective_seed_zero(monkeypatch):
    captured = {}
    fake_instance = SimpleNamespace(
        problem=SimpleNamespace(telemetry=None),
        pipeline_block="pipeline",
    )

    monkeypatch.setattr(pipeline, "maybe_known_key_fastpath", lambda **_kwargs: None)
    monkeypatch.setattr(pipeline, "build_cipher_config", lambda **_kwargs: object())
    monkeypatch.setattr(
        pipeline.ProblemInstance,
        "materialise",
        staticmethod(lambda _spec: fake_instance),
    )

    def fake_engine_solve(_instance, cfg):
        captured["seed"] = cfg.seed
        return "engine-result"

    monkeypatch.setattr(pipeline, "engine_solve", fake_engine_solve)
    monkeypatch.setattr(
        pipeline,
        "finalize_solution",
        lambda _problem, result, **_kwargs: result,
    )

    result = pipeline.execute_run(
        ciphertext=np.array([0], dtype=np.uint8),
        wli=None,
        cipher=object(),
        key=object(),
        solver=SimpleNamespace(name="beam", params={}, seed=None),
        scoring=object(),
        scorer_name="rune",
        logging_config=None,
        logging_runtime={},
        initialize_logging=False,
        telemetry_on=False,
        device=object(),
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


def test_known_key_fastpath_uses_no_effective_seed_for_non_random_path(monkeypatch):
    import rune_decrypter_prime.core.engine as core_engine
    import rune_decrypter_prime.core.problem as core_problem

    captured = {}
    fake_instance = SimpleNamespace(problem=SimpleNamespace(), pipeline_block="pipeline")

    monkeypatch.setattr(
        core_problem.ProblemInstance,
        "materialise",
        staticmethod(lambda _spec: fake_instance),
    )

    def fake_engine_solve(_instance, cfg):
        captured["seed"] = cfg.seed
        return "fast-result"

    monkeypatch.setattr(core_engine, "solve", fake_engine_solve, raising=False)
    monkeypatch.setattr(
        fastpaths,
        "finalize_solution",
        lambda _problem, result, **_kwargs: result,
    )

    result = fastpaths.maybe_known_key_fastpath(
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.const(value=0),
        ciphertext=np.array([0], dtype=np.uint8),
        wli=None,
        device=object(),
        scoring=object(),
        scorer_name="rune",
        logging_runtime={},
        encoding_dir=Direction.RTL,
        telemetry_on=False,
    )

    assert result == "fast-result"
    assert captured["seed"] is None
