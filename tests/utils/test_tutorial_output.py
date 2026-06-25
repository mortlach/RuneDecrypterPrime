from __future__ import annotations

import pytest

from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_output import (
    print_tutorial_debug_preview,
    tutorial_debug_preview_block,
    tutorial_debug_preview_lines,
)


def test_tutorial_debug_preview_prints_unambiguous_text_views() -> None:
    idx, wli, _ = Runeglish.encode_english_to_runes("READ THE WORDS", direction=Direction.RTL.value)

    lines = tutorial_debug_preview_lines(
        label="plaintext",
        idx=idx,
        wli=wli,
        direction=Direction.RTL,
    )
    text = "\n".join(lines)

    assert "Debug preview: plaintext" in text
    assert "encoding_dir: rtl" in text
    assert "latin_tokens:" in text
    assert "rune_indices:" in text
    assert "runes:" in text
    assert "R|AE|D" in text
    assert "T|H|E" in text
    rune_line = next(line for line in lines if line.startswith("runes:"))
    assert "|" not in rune_line


def test_tutorial_debug_preview_marks_truncation() -> None:
    idx, wli, _ = Runeglish.encode_english_to_runes("WHEN THE WHITE RABBIT READ", direction=Direction.RTL.value)

    text = "\n".join(
        tutorial_debug_preview_lines(
            label="plaintext",
            idx=idx,
            wli=wli,
            direction=Direction.RTL,
            token_limit=3,
        )
    )

    assert "<" in text
    assert "more>" in text


def test_tutorial_debug_preview_block_uses_standard_printer_style() -> None:
    idx, wli, _ = Runeglish.encode_english_to_runes("READ THE WORDS", direction=Direction.RTL.value)

    text = tutorial_debug_preview_block(label="plaintext", idx=idx, wli=wli, direction=Direction.RTL)

    assert "Debug preview: plaintext" in text
    assert "encoding_dir" in text
    assert "rtl" in text
    assert "latin_tokens" in text
    assert "rune_indices" in text
    assert "runes" in text
    assert "R|AE|D" in text
    assert "T|H|E" in text
    rune_line = next(line for line in text.splitlines() if line.startswith("runes"))
    assert "|" not in rune_line


def test_print_tutorial_debug_preview_uses_standard_block(capsys: pytest.CaptureFixture[str]) -> None:
    idx, wli, _ = Runeglish.encode_english_to_runes("THE", direction=Direction.RTL.value)

    print_tutorial_debug_preview(label="ciphertext", idx=idx, wli=wli, direction="rtl")

    out = capsys.readouterr().out
    assert "Debug preview: ciphertext" in out
    assert "encoding_dir" in out
    assert "rtl" in out
    assert "T|H|E" in out
