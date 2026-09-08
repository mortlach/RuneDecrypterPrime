from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.tier_a

ROOT = Path(__file__).resolve().parents[2]
ROUTE = ROOT / "solving" / "lp_getting_started"
LESSONS = (
    "01_load_welcome_pilgrim.py",
    "02_try_vigenere.py",
    "03_add_interruptors.py",
    "04_try_reverse_shifts.py",
    "05_let_rdp_search.py",
    "06_explore_an_end.py",
)


def _lesson(number: int, name: str):
    return importlib.import_module(f"solving.lp_getting_started.{number:02d}_{name}")


def test_lp_learning_route_has_the_six_reviewed_lessons() -> None:
    assert tuple(path.name for path in sorted(ROUTE.glob("[0-9][0-9]_*.py"))) == LESSONS
    assert (ROUTE / "README.md").is_file()


def test_lp_learning_lessons_use_only_public_rdp_entry_points() -> None:
    for filename in LESSONS:
        source = (ROUTE / filename).read_text(encoding="utf-8")
        assert "from rdp import api" in source
        assert "from tests" not in source
        assert "import tests" not in source
        assert "solving.solved_lp" not in source
        assert "sys.path" not in source
        compile(source, str(ROUTE / filename), "exec")


def test_recovered_lessons_import_without_running_searches() -> None:
    for filename in LESSONS:
        importlib.import_module(
            f"solving.lp_getting_started.{Path(filename).stem}"
        )


def test_incomplete_vigenere_lesson_keeps_the_reviewed_bounded_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lesson = _lesson(2, "try_vigenere")
    requests = []

    def fake_run(request):
        requests.append(request)
        return SimpleNamespace(key=(0,) * 8, score=0.0, plaintext_runes="ᚠ")

    monkeypatch.setattr(lesson.api, "run", fake_run)
    lesson.main()

    request = requests[0]
    assert request.problem_input.ref["label"] == "red_rune.welcome_pilgrim"
    assert request.cipher.kind.value == "vigenere"
    assert request.key_space.parameters["length"] == lesson.KEY_LENGTH == 8
    assert request.solver.parameters["width"] == 64
    assert request.solver.parameters["rounds"] is None
    assert request.interruptors is None


def test_interruptor_lesson_keeps_truth_out_of_the_search_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lesson = _lesson(3, "add_interruptors")
    requests = []

    def fake_run(request):
        requests.append(request)
        return SimpleNamespace(
            key=(0,) * (lesson.KEY_LENGTH + lesson.INTERRUPTOR_COUNT),
            score=0.0,
            plaintext_runes=lesson.REFERENCE_RUNES,
        )

    monkeypatch.setattr(lesson.api, "run", fake_run)
    lesson.main()

    request = requests[0]
    params = request.interruptors.parameters
    assert request.problem_input.ref["label"] == "red_rune.welcome_pilgrim"
    assert request.key_space.parameters["length"] == lesson.KEY_LENGTH == 8
    assert params["minimum_count"] == lesson.INTERRUPTOR_COUNT == 11
    assert params["maximum_count"] == lesson.INTERRUPTOR_COUNT
    assert len(params["candidate_positions"]) == 25
    assert "plaintext" not in repr(request).lower()
    assert "truth" not in repr(request).lower()


def test_reverse_shift_lesson_enumerates_the_complete_involutive_family() -> None:
    lesson = _lesson(4, "try_reverse_shifts")
    ciphertext = (0, 1, 7, 28)
    plaintexts = tuple(
        tuple((28 - value + shift) % 29 for value in ciphertext)
        for shift in range(29)
    )
    assert len(set(plaintexts)) == 29
    for shift, plaintext in enumerate(plaintexts):
        assert tuple((28 - value + shift) % 29 for value in plaintext) == ciphertext
    assert lesson.ORDER_WEIGHTS == {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25}


def test_an_end_lesson_searches_all_small_interruptor_subsets() -> None:
    lesson = _lesson(6, "explore_an_end")
    subsets = lesson.all_subsets((1, 3, 5, 7, 9))
    assert len(subsets) == 32
    assert len(set(subsets)) == 32
    assert lesson.decrypt_stream(
        (1, 2, 3),
        [1, 2],
        offset=0,
        shift=0,
        interruptors=frozenset({1}),
    ) == (0, 2, 1)


def test_truth_checks_follow_candidate_ranking_in_scoring_lessons() -> None:
    reverse_source = (ROUTE / "04_try_reverse_shifts.py").read_text(
        encoding="utf-8"
    )
    assert reverse_source.index("api.score_many(") < reverse_source.index(
        "Known shift ranks first:"
    )

    search_source = (ROUTE / "05_let_rdp_search.py").read_text(encoding="utf-8")
    assert search_source.index("api.score_many(") < search_source.index(
        "Same plaintext"
    )

    source = (ROUTE / "06_explore_an_end.py").read_text(encoding="utf-8")
    second_ranking = source.rindex("api.score_many(")
    assert second_ranking < source.index("# Only now compare")
    assert source.index("# Only now compare") < source.index("reference = tuple")
