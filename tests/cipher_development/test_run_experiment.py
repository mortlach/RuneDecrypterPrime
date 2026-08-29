from __future__ import annotations
import importlib
import json
from pathlib import Path
import pytest
from cipher_development import run_experiment as entry
from cipher_development.autokey_search import experiment as autokey
from cipher_development.two_period_overlay import pack09
from tools.robustness import cipher_solver_campaign as campaign

pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]


def test_documented_experiments_match_entry_point_registry() -> None:
    text = (ROOT / "cipher_development" / "README.md").read_text(encoding="utf-8")
    assert set(entry.EXPERIMENTS) == {"autokey", "two_period_pack09"}
    assert all((f"`{name}`" in text for name in entry.EXPERIMENTS))


def test_every_retained_experiment_imports() -> None:
    modules = (
        "cipher_development.autokey_search.experiment",
        "cipher_development.two_period_overlay.pack09",
    )
    assert all((importlib.import_module(name) for name in modules))


def test_unknown_experiment_and_mode_fail_clearly(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown experiment"):
        entry.run_selected(
            experiment="missing", mode="smoke", seed=1, output_location=tmp_path
        )
    with pytest.raises(ValueError, match="MODE"):
        entry.run_selected(
            experiment="autokey", mode="unknown", seed=1, output_location=tmp_path
        )


def test_output_location_must_be_external() -> None:
    with pytest.raises(ValueError, match="absolute external"):
        entry.run_selected(
            experiment="autokey",
            mode="smoke",
            seed=1,
            output_location=Path("relative-output"),
        )
    with pytest.raises(ValueError, match="outside the repository"):
        entry.run_selected(
            experiment="autokey", mode="smoke", seed=1, output_location=ROOT / "output"
        )
    with pytest.raises(ValueError, match="absolute external"):
        autokey.run_experiment(
            mode="smoke", seed=1, output_root=Path("relative-output")
        )
    with pytest.raises(ValueError, match="absolute external"):
        pack09.run_experiment(
            mode="smoke", seed=pack09.MASTER_SEED, output_root=Path("relative-output")
        )


def test_smoke_trial_selection_is_deterministic() -> None:
    assert autokey.trial_indices("smoke", 20260822) == autokey.trial_indices(
        "smoke", 20260822
    )
    assert len(autokey.trial_indices("smoke", 20260822)) == 1
    with pytest.raises(ValueError, match="tools/robustness"):
        autokey.trial_indices("development", 20260822)


def test_autokey_delegates_to_exact_canonical_recipe() -> None:
    recipe = campaign.resolved_recipe(autokey.FAMILY)
    assert recipe.recipe_id == "autokey_wli12_beam_v1"
    assert campaign.config.scoring_to_dict(recipe.scoring) == {
        "objective": "pct.logp.win10",
        "include_char": False,
        "use_word_breaks": True,
        "char_weights": {},
        "wli_weights": {1: 0.3, 2: 0.7},
    }
    source = Path(autokey.__file__).read_text(encoding="utf-8")
    for duplicate in ("SCORER_PROFILES", "BEAM_PARAMS", "SolverSpec"):
        assert duplicate not in source


def test_entry_point_prints_resolved_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "result.json"
    destination.write_text(json.dumps({"ok": True}), encoding="utf-8")
    definition = entry.ExperimentDefinition(
        recipe_profile="test_recipe_v1",
        smoke_assets="ci_light",
        development_assets="full_v1",
        run=lambda mode, seed, output: destination,
    )
    monkeypatch.setitem(entry.EXPERIMENTS, "test", definition)
    assert (
        entry.run_selected(
            experiment="test", mode="smoke", seed=7, output_location=tmp_path
        )
        == destination
    )
    output = capsys.readouterr().out
    for expected in (
        "experiment: test",
        "mode: smoke",
        "recipe/profile: test_recipe_v1",
        "seed: 7",
        "asset profile: ci_light",
        str(tmp_path.resolve()),
    ):
        assert expected in output


def test_pack09_declares_full_asset_development_boundary() -> None:
    definition = entry.EXPERIMENTS["two_period_pack09"]
    assert definition.smoke_assets == "ci_light"
    assert definition.development_assets == "full_v1"
