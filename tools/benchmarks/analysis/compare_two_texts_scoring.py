"""
Compare two plaintext strings under many scoring methods.

Purpose:
  - show how char and WLI scoring (n=1..4 and combos) rank two candidate texts
  - help diagnose cases where a solver score looks "too good"

Usage:
  - edit TEXT_A / TEXT_B / DIRECTION at the top
  - run:
      python tools/benchmarks/analysis/compare_two_texts_scoring.py
"""

from __future__ import annotations

import sys
from pathlib import Path as _Path

_cur = _Path(__file__).resolve()
_ROOT = _cur
for _parent in [_cur.parent, *_cur.parents]:
    if (_parent / "src" / "rune_decrypter_prime").exists():
        _ROOT = _parent
        break
_SRC = _ROOT / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
from rune_decrypter_prime.utils.text_scoring_comparison import compare_two_texts, format_score_rows


# ---------------- editable inputs ----------------
DIRECTION = Direction.LTR

_BASE = long_plaintext_string[:900]
TEXT_A = _BASE
TEXT_B = " ".join(reversed(_BASE.split()))
# -------------------------------------------------


def main() -> None:
    rows = compare_two_texts(TEXT_A, TEXT_B, direction=DIRECTION)
    print("[compare] text A vs text B scoring")
    print(f"[compare] direction={DIRECTION.value} lenA={len(TEXT_A)} lenB={len(TEXT_B)}")
    print(format_score_rows(rows, label_a="score_A", label_b="score_B"))


if __name__ == "__main__":
    main()
