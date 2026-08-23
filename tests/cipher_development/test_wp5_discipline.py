from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_lessons_preserve_current_development_discipline() -> None:
    text = (ROOT / "cipher_development/LESSONS.md").read_text(encoding="utf-8")
    for conclusion in (
        "Diagnose scoring before increasing search",
        "Select by search-visible score only",
        "Freeze candidate recipes during qualification",
        "Separate stochastic failure from systematic mis-ranking",
        "Keep investigations local",
    ):
        assert conclusion in text


def test_readme_defines_boundaries_and_external_output() -> None:
    text = (ROOT / "cipher_development/README.md").read_text(encoding="utf-8")
    for boundary in (
        "src/rune_decrypter_prime/", "tutorials/", "tools/robustness/",
        "run_outputs/cipher_development/", "ci_light", "full_v1",
        "Truth", "CAMPAIGN_RECIPES",
    ):
        assert boundary in text
    assert "output/cipher_development/" not in text


def test_retained_replay_adapter_does_not_call_search() -> None:
    path = ROOT / "cipher_development/two_period_overlay/replay.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {
        "run_search", "run_case", "coordinate_search", "anneal_and_polish",
        "generate_seed_keys_periodic_columnar",
    }
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not (called & forbidden)


def test_no_duplicate_campaign_implementation_remains() -> None:
    root = ROOT / "cipher_development"
    runner_names = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if path.name in {"run.py", "run_pack08.py", "search.py"}
    }
    assert runner_names == set()


def test_run_experiment_is_the_only_directly_executable_development_file() -> None:
    root = ROOT / "cipher_development"
    executable = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if '__name__ == "__main__"' in path.read_text(encoding="utf-8")
    }
    assert executable == {"run_experiment.py"}


def test_retained_development_has_no_repository_local_output_default() -> None:
    for path in (ROOT / "cipher_development").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert 'Path("output/' not in text
        assert "output_root: Path =" not in text
