from __future__ import annotations

from pathlib import Path

import pytest

from rune_decrypter_prime.utils.tutorial_benchmark import TutorialAcceptanceKind
from rune_decrypter_prime.utils.tutorial_runner import (
    ConsoleOutput,
    TutorialEntry,
    TutorialRunSet,
    parse_match_ratio,
    repo_relpath,
    select_tutorials,
    tail_text,
    validate_tutorial_entries,
)


def test_tutorial_runner_enums_are_plain_stable_labels() -> None:
    assert [item.value for item in TutorialRunSet] == [
        "fast",
        "release",
        "extended",
        "partial_recovery",
        "ci_light",
        "full_assets",
        "all_working",
    ]
    assert [item.value for item in ConsoleOutput] == ["compact", "full"]


def test_select_tutorials_uses_named_run_sets() -> None:
    entries = (
        TutorialEntry("Tutorial_A.py", 1.0, run_sets=(TutorialRunSet.FAST, TutorialRunSet.RELEASE)),
        TutorialEntry("Tutorial_B.py", 0.9, TutorialAcceptanceKind.PARTIAL_RECOVERY, (TutorialRunSet.PARTIAL_RECOVERY,)),
    )

    assert select_tutorials(entries, TutorialRunSet.FAST) == (entries[0],)
    assert select_tutorials(entries, TutorialRunSet.PARTIAL_RECOVERY) == (entries[1],)
    assert select_tutorials(entries, TutorialRunSet.ALL_WORKING) == entries
    assert entries[0].required_asset_profile == "ci_light"


def test_validate_tutorial_entries_checks_shape_and_files(tmp_path: Path) -> None:
    tutorial = tmp_path / "Tutorial_A.py"
    tutorial.write_text("print('ok')\n", encoding="utf-8")
    validate_tutorial_entries(
        (TutorialEntry("Tutorial_A.py", 1.0),),
        tutorial_dir=tmp_path,
        run_set=TutorialRunSet.RELEASE,
    )

    with pytest.raises(ValueError, match="simple Python filename"):
        validate_tutorial_entries(
            (TutorialEntry("../Tutorial_A.py", 1.0),),
            tutorial_dir=tmp_path,
            run_set=TutorialRunSet.RELEASE,
        )


def test_parse_match_ratio_reads_last_reported_value() -> None:
    text = "Match ratio: 0.500\nmatch_ratio : 0.901\n"

    assert parse_match_ratio(text) == pytest.approx(0.901)


def test_tail_text_and_repo_relpath_helpers(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    target = root / "output" / "tutorial_logs" / "Tutorial_A.txt"
    target.parent.mkdir(parents=True)
    target.write_text("x\n", encoding="utf-8")

    assert tail_text("a\nb\nc\n", lines=2) == "b\nc"
    assert repo_relpath(target, repo_root=root) == "output/tutorial_logs/Tutorial_A.txt"
