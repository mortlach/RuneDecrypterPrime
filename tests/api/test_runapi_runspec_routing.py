from __future__ import annotations

import importlib
from types import SimpleNamespace

import numpy as np
import pytest

from rune_decrypter_prime.api import fastpaths, pipeline
from rune_decrypter_prime.api.run import RunAPI
from rune_decrypter_prime.api.run_spec import NormalizedInput, RawTextInput, RunSpec, SourceInputRef
from rune_decrypter_prime.api.source_resolution import ResolvedSourceInput
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rune_decrypter_prime.core.types import Device, Direction
from rune_decrypter_prime.data.liber_primus.lp_master import MASTER_TRANSCRIPT_ASSET_ID


def _minimal_spec(
    problem_input,
    *,
    key=None,
    solver=None,
    logging=None,
) -> RunSpec:
    return RunSpec(
        problem_input=problem_input,
        cipher=CipherSpec.periodic_substitution(period=1),
        key=key or KeySpec.repeat(len=1),
        solver=solver or SolverSpec.beam(beam_width=1, seed=1),
        logging=logging,
        telemetry_on=False,
    )


def _capture_run_execute(monkeypatch):
    captured = {}

    def fake_execute_run(**kwargs):
        captured.update(kwargs)
        return "ok"

    run_module = importlib.import_module("rune_decrypter_prime.api.run")
    monkeypatch.setattr(run_module, "execute_run", fake_execute_run)
    return captured


def _valid_locator_ref() -> dict[str, object]:
    return {
        "page_scheme": "canon_unsolved_page",
        "page_number": 54,
        "line": 0,
        "line_end": 2,
        "word": None,
        "word_end": None,
        "route_kind": "none",
    }


def test_existing_runapi_text_path_still_routes_to_execute_run(monkeypatch) -> None:
    captured = _capture_run_execute(monkeypatch)

    result = RunAPI.run(
        text=[0],
        cipher=CipherSpec.periodic_substitution(period=1),
        key=KeySpec.repeat(len=1),
        solver=SolverSpec.beam(beam_width=1, seed=1),
        telemetry_on=False,
    )

    assert result == "ok"
    assert captured["ciphertext"].tolist() == [0]
    assert captured["encoding_dir"] is Direction.RTL


def test_runspec_raw_text_uses_raw_text_normalization(monkeypatch) -> None:
    captured = _capture_run_execute(monkeypatch)
    spec = _minimal_spec(RawTextInput("abc"))

    result = RunAPI.run(spec=spec)

    assert result == "ok"
    assert captured["ciphertext"].dtype == np.uint8
    assert captured["ciphertext"].flags.c_contiguous
    assert captured["ciphertext"].size > 0
    assert captured["wli"] is not None
    assert len(captured["wli"]) == int(captured["ciphertext"].size)


def test_runspec_raw_text_with_spaces_infers_wli(monkeypatch) -> None:
    captured = _capture_run_execute(monkeypatch)
    spec = _minimal_spec(RawTextInput("abc def"))

    RunAPI.run(spec=spec)

    wli = captured["wli"]
    assert wli is not None
    assert len(wli) == int(captured["ciphertext"].size)
    assert any(pair[0] == 0 for pair in wli[1:])


def test_runspec_normalized_input_with_no_wli_passes_none(monkeypatch) -> None:
    captured = _capture_run_execute(monkeypatch)
    spec = _minimal_spec(NormalizedInput(ct_idx=[1, 2, 3], wli=None))

    RunAPI.run(spec=spec)

    assert captured["ciphertext"].tolist() == [1, 2, 3]
    assert captured["ciphertext"].dtype == np.uint8
    assert captured["ciphertext"].flags.c_contiguous
    assert captured["wli"] is None


def test_runspec_normalized_input_with_wli_passes_stored_wli(monkeypatch) -> None:
    captured = _capture_run_execute(monkeypatch)
    spec = _minimal_spec(NormalizedInput(ct_idx=[1, 2], wli=[(0, 1), (0, 1)]))

    RunAPI.run(spec=spec)

    assert captured["ciphertext"].tolist() == [1, 2]
    assert captured["wli"] == ((0, 1), (0, 1))
    assert spec.problem_input.ct_idx == (1, 2)


def test_runspec_source_input_ref_calls_resolver_and_routes_resolved_input(monkeypatch) -> None:
    captured = _capture_run_execute(monkeypatch)
    calls = []
    source_ref = SourceInputRef(
        source_kind="other.source",
        asset_id="asset",
        asset_version="version",
        ref={"selector": "one"},
    )

    def fake_resolver(ref):
        calls.append(ref)
        return ResolvedSourceInput(
            ct_idx=[4, 5],
            wli=[[0, 1], [0, 1]],
            source_ref=ref,
            source_metadata={"source": "test"},
        )

    routing_module = importlib.import_module("rune_decrypter_prime.api.run_spec_routing")
    monkeypatch.setattr(routing_module, "resolve_source_input_ref", fake_resolver)

    RunAPI.run(spec=_minimal_spec(source_ref))

    assert calls == [source_ref]
    assert captured["ciphertext"].tolist() == [4, 5]
    assert captured["wli"] == ((0, 1), (0, 1))
    assert "source_metadata" not in captured


def test_runspec_source_input_ref_stale_version_fails_through_resolver(monkeypatch) -> None:
    _capture_run_execute(monkeypatch)
    source_ref = SourceInputRef(
        source_kind="liber_primus.locator",
        asset_id=MASTER_TRANSCRIPT_ASSET_ID,
        asset_version="stale-version",
        ref=_valid_locator_ref(),
    )

    with pytest.raises(ValueError, match="asset_version"):
        RunAPI.run(spec=_minimal_spec(source_ref))


def test_runspec_logging_config_initializes_durable_logging(monkeypatch) -> None:
    captured = _capture_run_execute(monkeypatch)
    cfg = LoggingConfig(write_jsonl=False)
    spec = _minimal_spec(RawTextInput("abc"), logging=cfg)

    RunAPI.run(spec=spec)

    assert captured["logging_config"] is cfg
    assert captured["logging_runtime"] == {}
    assert captured["initialize_logging"] is True


def test_runspec_allows_runtime_logging_controls_outside_spec(monkeypatch) -> None:
    captured = _capture_run_execute(monkeypatch)
    callback = lambda *_args, **_kwargs: None

    RunAPI.run(
        spec=_minimal_spec(RawTextInput("abc")),
        logging={"progress_callback": callback, "log_interval": 10},
    )

    assert captured["logging_runtime"] == {
        "progress_callback": callback,
        "log_interval": 10,
    }
    assert captured["logging_config"] is None
    assert captured["initialize_logging"] is False


@pytest.mark.parametrize(
    "logging",
    [
        LoggingConfig(write_jsonl=False),
        {"portable_output": True},
        {"verbose": False},
        {"portable": True},
        {"unknown": True},
    ],
)
def test_runspec_rejects_non_runtime_logging_outside_spec(monkeypatch, logging) -> None:
    _capture_run_execute(monkeypatch)

    with pytest.raises((TypeError, ValueError)):
        RunAPI.run(spec=_minimal_spec(RawTextInput("abc")), logging=logging)


def test_runspec_rejects_mixed_text_input(monkeypatch) -> None:
    _capture_run_execute(monkeypatch)

    with pytest.raises(TypeError, match="text"):
        RunAPI.run([0], spec=_minimal_spec(RawTextInput("abc")))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cipher": CipherSpec.periodic_substitution(period=1)},
        {"key": KeySpec.repeat(len=1)},
        {"solver": SolverSpec.beam(beam_width=1)},
    ],
)
def test_runspec_rejects_mixed_cipher_key_solver(monkeypatch, kwargs) -> None:
    _capture_run_execute(monkeypatch)

    with pytest.raises(TypeError):
        RunAPI.run(spec=_minimal_spec(RawTextInput("abc")), **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"wli_data": [(0, 1)]},
        {"force_no_wli": False},
    ],
)
def test_runspec_rejects_mixed_wli_controls(monkeypatch, kwargs) -> None:
    _capture_run_execute(monkeypatch)

    with pytest.raises(TypeError):
        RunAPI.run(spec=_minimal_spec(RawTextInput("abc")), **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"initial_keys": [[0]]},
        {"interruptors": {}},
        {"interruptors_exact": [1]},
        {"interruptors_pool": [1]},
        {"interruptors_max": 1},
    ],
)
def test_runspec_rejects_mixed_initial_keys_and_interruptor_controls(monkeypatch, kwargs) -> None:
    _capture_run_execute(monkeypatch)

    with pytest.raises(TypeError):
        RunAPI.run(spec=_minimal_spec(RawTextInput("abc")), **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"device": Device.CPU},
        {"scorer": "rune"},
        {"scorer_params": {}},
        {"telemetry_on": False},
        {"encoding_dir": Direction.RTL},
        {"initial_text_permutation_indices": [0]},
    ],
)
def test_runspec_rejects_remaining_mixed_durable_inputs(monkeypatch, kwargs) -> None:
    _capture_run_execute(monkeypatch)

    with pytest.raises(TypeError):
        RunAPI.run(spec=_minimal_spec(RawTextInput("abc")), **kwargs)


def test_runspec_ordinary_solver_omitted_seed_still_uses_effective_seed_zero(monkeypatch) -> None:
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
    monkeypatch.setattr(pipeline, "finalize_solution", lambda _problem, result, **_kwargs: result)

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


def test_runspec_known_key_fastpath_still_uses_seed_none(monkeypatch) -> None:
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
    monkeypatch.setattr(fastpaths, "finalize_solution", lambda _problem, result, **_kwargs: result)

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
