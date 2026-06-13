from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

import rune_decrypter_prime
from rune_decrypter_prime.api.run import RunAPI
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.problem.spec import ProblemSpec
from rune_decrypter_prime.core.types import ScorerImpl
from rune_decrypter_prime.scoring.rune_scorer import RuneScorer


def _cipher_config() -> CipherConfig:
    return CipherConfig(ciphertext=[1, 2, 3], wli_data=[], key_length=3, name="vigenere")


def _minimal_lm_root(tmp_path: Path) -> Path:
    lm_root = tmp_path / "minimal_lm"
    lm_root.mkdir()
    (lm_root / "index.json").write_text(
        json.dumps(
            {
                "version": "test-minimal",
                "base": ".",
                "ecdf_root": ".",
                "joint_root": ".",
                "models": {},
            }
        ),
        encoding="utf-8",
    )
    return lm_root


def _scoring_config(model_root: Path | None = None) -> ScoringConfig:
    return ScoringConfig(impl=ScorerImpl.NUMPY, model_root=model_root)


def test_problem_spec_accepts_canonical_configs() -> None:
    spec = ProblemSpec(text="", cipher_cfg=_cipher_config(), scorer_params=_scoring_config())

    assert isinstance(spec.cipher_cfg, CipherConfig)
    assert isinstance(spec.scorer_params, ScoringConfig)


def test_problem_spec_rejects_dict_cipher_cfg() -> None:
    with pytest.raises(TypeError, match="cipher_cfg must be CipherConfig"):
        ProblemSpec(text="", cipher_cfg={}, scorer_params=_scoring_config())


def test_problem_spec_rejects_dict_scorer_params() -> None:
    with pytest.raises(TypeError, match="scorer_params must be ScoringConfig"):
        ProblemSpec(text="", cipher_cfg=_cipher_config(), scorer_params={})


def test_decryption_problem_rejects_dict_c_cfg() -> None:
    with pytest.raises(TypeError, match="c_cfg must be CipherConfig"):
        DecryptionProblem(cipher=object(), scorer=object(), c_cfg={}, s_cfg=_scoring_config())


def test_decryption_problem_rejects_dict_s_cfg() -> None:
    with pytest.raises(TypeError, match="s_cfg must be ScoringConfig"):
        DecryptionProblem(cipher=object(), scorer=object(), c_cfg=_cipher_config(), s_cfg={})


def test_build_scorer_accepts_canonical_configs(tmp_path: Path) -> None:
    c_cfg = _cipher_config()
    s_cfg = _scoring_config(_minimal_lm_root(tmp_path))

    scorer = build_scorer(c_cfg, s_cfg)

    assert isinstance(scorer, RuneScorer)


def test_build_scorer_rejects_dict_c_cfg() -> None:
    with pytest.raises(TypeError, match="cfg_cipher must be CipherConfig"):
        build_scorer({}, _scoring_config())


def test_build_scorer_rejects_dict_s_cfg() -> None:
    with pytest.raises(TypeError, match="s_cfg must be ScoringConfig"):
        build_scorer(_cipher_config(), {})


def test_rune_scorer_rejects_dict_scorer_cfg_before_backend_load() -> None:
    with pytest.raises(TypeError, match="scorer_cfg must be ScoringConfig"):
        RuneScorer(_cipher_config(), {})  # type: ignore[arg-type]


def test_runapi_accepts_user_facing_scorer_params_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_execute_run(**kwargs):
        captured["scoring"] = kwargs["scoring"]
        return {"ok": True}

    run_module = importlib.import_module("rune_decrypter_prime.api.run")
    monkeypatch.setattr(run_module, "execute_run", fake_execute_run)

    result = RunAPI.run(
        [1, 2, 3],
        cipher=CipherSpec.periodic_substitution(period=3),
        key=KeySpec.repeat(len=3),
        solver=SolverSpec.beam(beam_width=1),
        scorer_params={"impl": "numpy", "dtype": "float32", "include_char": False},
    )

    assert result == {"ok": True}
    assert isinstance(captured["scoring"], ScoringConfig)
    assert captured["scoring"].include_char is False


def test_core_config_public_import_surface_is_package_reexport() -> None:
    from rune_decrypter_prime.core.config import CipherConfig as ImportedCipherConfig
    from rune_decrypter_prime.core.config import ScoringConfig as ImportedScoringConfig

    config_module = importlib.import_module("rune_decrypter_prime.core.config")
    module_path = Path(config_module.__file__).resolve()
    package_root = Path(rune_decrypter_prime.__file__).resolve().parent

    assert ImportedCipherConfig is CipherConfig
    assert ImportedScoringConfig is ScoringConfig
    assert module_path == package_root / "core" / "config" / "__init__.py"
    assert not (package_root / "core" / "config.py").exists()
