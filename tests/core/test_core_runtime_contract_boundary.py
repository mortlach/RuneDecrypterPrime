from __future__ import annotations
from rdp import api
import importlib
import json
from pathlib import Path
import pytest
import rdp
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rdp.core.problem.runtime import DecryptionProblem
from rdp.core.problem.spec import ProblemSpec
from rdp.scoring.rune_scorer import RuneScorer
from rdp.scoring.unified_rune_scorer import UnifiedRuneScorer

def _cipher_config() -> CipherConfig:
    return CipherConfig(ciphertext=[1, 2, 3], wli_data=[], key_length=3, name='vigenere')

def _minimal_lm_root(tmp_path: Path) -> Path:
    lm_root = tmp_path / 'minimal_lm'
    lm_root.mkdir()
    (lm_root / 'index.json').write_text(json.dumps({'version': 'test-minimal', 'base': '.', 'ecdf_root': '.', 'joint_root': '.', 'models': {}}), encoding='utf-8')
    return lm_root


def _scoring_config(model_root: Path | None = None) -> ScoringConfig:
    return api.ScoringConfig(
        backend=api.advanced.ScorerBackend.NUMPY,
        language_model_root=model_root,
    )


def test_problem_spec_accepts_canonical_configs() -> None:
    spec = ProblemSpec(text='', cipher_cfg=_cipher_config(), scorer_params=_scoring_config())
    assert isinstance(spec.cipher_cfg, CipherConfig)
    assert isinstance(spec.scorer_params, ScoringConfig)

def test_problem_spec_rejects_dict_cipher_cfg() -> None:
    with pytest.raises(TypeError, match='cipher_cfg must be CipherConfig'):
        ProblemSpec(text='', cipher_cfg={}, scorer_params=_scoring_config())

def test_problem_spec_rejects_dict_scorer_params() -> None:
    with pytest.raises(TypeError, match='scorer_params must be ScoringConfig'):
        ProblemSpec(text='', cipher_cfg=_cipher_config(), scorer_params={})

def test_decryption_problem_rejects_dict_c_cfg() -> None:
    with pytest.raises(TypeError, match='c_cfg must be CipherConfig'):
        DecryptionProblem(cipher=object(), scorer=object(), c_cfg={}, s_cfg=_scoring_config())

def test_decryption_problem_rejects_dict_s_cfg() -> None:
    with pytest.raises(TypeError, match='s_cfg must be ScoringConfig'):
        DecryptionProblem(cipher=object(), scorer=object(), c_cfg=_cipher_config(), s_cfg={})

def test_build_scorer_accepts_canonical_configs(tmp_path: Path) -> None:
    c_cfg = _cipher_config()
    s_cfg = _scoring_config(_minimal_lm_root(tmp_path))
    scorer = build_scorer(c_cfg, s_cfg)
    assert isinstance(scorer, RuneScorer)

def test_build_scorer_rejects_dict_c_cfg() -> None:
    with pytest.raises(TypeError, match='cfg_cipher must be CipherConfig'):
        build_scorer({}, _scoring_config())

def test_build_scorer_rejects_dict_s_cfg() -> None:
    with pytest.raises(TypeError, match='s_cfg must be ScoringConfig'):
        build_scorer(_cipher_config(), {})

def test_rune_scorer_rejects_dict_scorer_cfg_before_backend_load() -> None:
    with pytest.raises(TypeError, match='scorer_cfg must be ScoringConfig'):
        RuneScorer(_cipher_config(), {})

def test_unified_rune_scorer_rejects_dict_cipher_cfg_before_backend_load() -> None:
    with pytest.raises(TypeError, match='cfg_cipher must be CipherConfig'):
        UnifiedRuneScorer({}, _scoring_config())

def test_unified_rune_scorer_rejects_dict_scorer_cfg_before_backend_load() -> None:
    with pytest.raises(TypeError, match='cfg_scorer must be ScoringConfig'):
        UnifiedRuneScorer(_cipher_config(), {})


def test_runapi_accepts_typed_public_scoring_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_execute_run(**kwargs):
        captured["scoring"] = kwargs["scoring"]
        return {"ok": True}

    run_module = importlib.import_module("rdp.api.run")
    monkeypatch.setattr(run_module, "execute_run", fake_execute_run)
    result = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(indices=[1, 2, 3]),
            cipher=api.CipherSpec.periodic_substitution(period=3),
            key_space=api.KeySpec.periodic_substitution(period=3),
            solver=api.SolverSpec.beam_search(width=1, rounds=0),
            scoring=api.ScoringConfig(
                character_lane_enabled=False,
                backend=api.advanced.ScorerBackend.NUMPY,
                compute_dtype=api.advanced.FloatDType.FLOAT32,
            ),
        )
    )
    assert isinstance(result, api.RunResult)
    assert isinstance(captured["scoring"], ScoringConfig)
    assert captured["scoring"].character_lane_enabled is False


def test_core_config_package_is_lightweight_and_uses_exact_owners() -> None:
    from rdp.core.config.cipher import CipherConfig as ImportedCipherConfig
    from rdp.core.config.scoring import ScoringConfig as ImportedScoringConfig

    config_module = importlib.import_module('rdp.core.config')
    module_path = Path(config_module.__file__).resolve()
    package_root = Path(rdp.__file__).resolve().parent
    assert ImportedCipherConfig is CipherConfig
    assert ImportedScoringConfig is ScoringConfig
    assert module_path == package_root / 'core' / 'config' / '__init__.py'
    assert not (package_root / 'core' / 'config.py').exists()
    assert not hasattr(config_module, 'CipherConfig')
    assert not hasattr(config_module, 'ScoringConfig')
