from __future__ import annotations
import rdp.api.pipeline_helpers
import numpy as np
from rdp.core.config.solution import Solution
from rdp.core.types import Direction
from rdp.data.runeglish import Runeglish
from rune_decrypter_prime.utils.solve_output import render_plaintext

def test_ensure_plaintext_rune_uses_encoding_direction_for_latin_display() -> None:
    pt_idx, wli, _rune_str = Runeglish.encode_english_to_runes('READ EARTH AETHER', direction='rtl')
    solution = Solution(key=[1], plaintext=np.asarray(pt_idx, dtype=np.uint8), score=0.0)
    rdp.api.pipeline_helpers.ensure_plaintext_rune(solution, ciphertext=np.asarray(pt_idx, dtype=np.uint8), wli=wli, cipher=None, encoding_dir=Direction.RTL)
    assert solution.plaintext_idx == pt_idx
    assert solution.plaintext_latin == 'READ EARTH AETHER'
    assert 'RAED' not in solution.plaintext_latin
    assert solution.direction is Direction.RTL

def test_solve_output_render_plaintext_accepts_direction() -> None:
    pt_idx, wli, _rune_str = Runeglish.encode_english_to_runes('READ', direction='rtl')
    latin, runes = render_plaintext(pt_idx, wli, direction=Direction.RTL)
    assert latin == 'READ'
    assert runes == 'ᚱᚫᛞ'
