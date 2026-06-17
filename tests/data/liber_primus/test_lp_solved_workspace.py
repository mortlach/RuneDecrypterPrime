from __future__ import annotations

import ast
from pathlib import Path

import pytest

from rune_decrypter_prime.data import liber_primus as lp

pytestmark = pytest.mark.tier_a

REPO_ROOT = Path(__file__).resolve().parents[3]
SOLVED_ROOT = REPO_ROOT / "solving" / "solved_lp"
KNOWN_SOLVED_LABELS = (
    "warning",
    "welcome_pilgrim",
    "some_wisdom",
    "koan_a_man",
    "loss_of_divinity",
    "koan_during_lesson",
    "instruction",
    "an_end",
    "parable",
)

WORKBOOK_FILES = (
    "01_A_Warning.py",
    "02_Welcome_Pilgrim.py",
    "03_Some_Wisdom.py",
    "04_Koan_A_Man.py",
    "05_Loss_Of_Divinity.py",
    "06_Koan_During_Lesson.py",
    "07_Instruction.py",
    "08_An_End.py",
    "09_Parable.py",
)


@pytest.mark.parametrize("label", KNOWN_SOLVED_LABELS)
def test_solved_lp_workspace_labels_resolve_to_payloads(label: str) -> None:
    payload = lp.payload_from_label(label)

    assert payload.ct_idx
    assert payload.wli
    assert payload.metadata["requested_label"] == label


def test_solved_lp_workspace_is_flat() -> None:
    assert [path.name for path in SOLVED_ROOT.iterdir() if path.is_dir()] == []


@pytest.mark.parametrize("filename", WORKBOOK_FILES)
def test_solved_lp_has_human_readable_files(filename: str) -> None:
    workbook_file = SOLVED_ROOT / filename
    tree = ast.parse(workbook_file.read_text(encoding="utf-8"))

    assert workbook_file.is_file()
    assert "main" in {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_solved_lp_examples_do_not_delegate_to_shared_helper_module() -> None:
    files = [path for path in SOLVED_ROOT.glob("*.py") if path.name != "run_all.py"]
    forbidden_helper = "_" + "common"

    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert not text.startswith("\ufeff")
        assert forbidden_helper not in text
        assert "from solving.solved_lp." not in text


def test_solved_lp_examples_use_main_page_metadata_names() -> None:
    files = [path for path in SOLVED_ROOT.glob("*.py") if path.name != "run_all.py"]

    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "main_page_start" in text
        assert "main_page_end" in text


@pytest.mark.parametrize(
    "path",
    (
        SOLVED_ROOT / "02_Welcome_Pilgrim.py",
    ),
)
def test_welcome_pilgrim_uses_divinity_period_and_zero_position_pool(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    stale_period = "KEY_LENGTH = " + "7"
    stale_pool = "CANONICAL" + "_INTERRUPTOR_POOL"

    assert 'KEY_TEXT_HINT = "DIVINITY"' in text
    assert "KEY_LENGTH = len(KEY_TEXT_HINT)" in text
    assert stale_period not in text
    assert stale_pool not in text
    assert "enumerate(ct_idx)" in text or "zero_positions(ct_idx)" in text
    assert "int(value) == 0" in text or "zero_positions(ct_idx)" in text
    assert "pool=interruptor_pool" in text
    assert "range(len(ct_idx))" not in text
    assert "os.environ" not in text


@pytest.mark.parametrize(
    "path",
    (
        SOLVED_ROOT / "06_Koan_During_Lesson.py",
    ),
)
def test_koan_during_lesson_workbook_pins_solved_count_two_replay(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    assert 'KEY_TEXT_HINT_HUMAN = "CIRCUMFERENCE"' in text
    assert 'RECIPE_REFERENCE_KEY_OR_SHIFT = "FIRFUMFERENFE"' in text
    assert "KEY_LENGTH = len(RECIPE_REFERENCE_KEY_OR_SHIFT)" in text
    assert "INTERRUPTOR_COUNT = len(PINNED_FOUND_INTERRUPTORS)" in text
    assert "PINNED_FOUND_INTERRUPTORS = [49, 58]" in text
    assert "ACCEPTANCE_MATCH_RATIO = 1.0" in text
    assert "CANONICAL_KOAN_DURING_LESSON_TEXT" in text
    assert "zero_positions(ct_idx)" in text
    assert "zero_positions(ct_idx)" in text
    assert "match_ratio(plaintext_idx, reference_idx)" in text
    assert '"solved" if ratio >= ACCEPTANCE_MATCH_RATIO else "diagnostic_not_yet_solved"' in text


@pytest.mark.parametrize(
    "path",
    (
        SOLVED_ROOT / "02_Welcome_Pilgrim.py",
    ),
)
def test_welcome_pilgrim_uses_pinned_beam_64_solver_variant(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    stale_variants = "SOLVER" + "_VARIANTS"
    assert stale_variants not in text
    assert 'SOLVER_VARIANT = "beam_64"' in text
    assert "SOLVER = SolverSpec.beam(" in text
    assert "beam_width=64" in text
    assert "plateau_rounds=5" in text
    assert "seed=2026" in text
    assert "score_time_s" in text


@pytest.mark.parametrize(
    "path",
    (
        SOLVED_ROOT / "02_Welcome_Pilgrim.py",
    ),
)
def test_welcome_pilgrim_uses_minimal_one_and_two_gram_scoring(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    assert "CHAR_NGRAM_WEIGHTS" in text
    assert "WLI_NGRAM_WEIGHTS" in text
    assert "char_weights=CHAR_NGRAM_WEIGHTS" in text or '"char_weights": CHAR_NGRAM_WEIGHTS' in text
    assert "wli_weights=WLI_NGRAM_WEIGHTS" in text or '"wli_weights": WLI_NGRAM_WEIGHTS' in text
    assert "CHAR_NGRAM_WEIGHTS = {1: 0.3, 2: 0.7}" in text
    assert "WLI_NGRAM_WEIGHTS = {1: 0.3, 2: 0.7}" in text
    stale_char = "CHAR_NGRAM_WEIGHTS = {" + "3:"
    stale_wli = "WLI_NGRAM_WEIGHTS = {" + "3:"
    assert stale_char not in text
    assert stale_wli not in text
