from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.utils.scheduled_stream_lookup_tutorial_utils import (
    concat_keys,
    encode_plaintext,
    key_period13,
    key_period31,
    mask_from_segments,
    run_real_key_recovery_demo,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    pt_idx, _wli, _pt_runes = encode_plaintext()
    n = len(pt_idx)
    key = concat_keys(key_period13(), key_period31())

    # User-defined mask schedule. Optimizer searches the 44 periodic key values.
    mask_13_31_13 = mask_from_segments(n, [("A", 0, 120), ("B", 120, 240), ("A", 240, None)])
    run_real_key_recovery_demo(
        title="REAL SOLVE scheduled_stream_lookup: recover segmented P13/P31/P13 key",
        cipher_name="two_period_vigenere",
        cipher_kwargs=dict(
            period_a=13,
            period_b=31,
            alphabet_size=29,
            schedule="mask",
            mask=mask_13_31_13,
        ),
        key_values=key,
        expected_key_len=44,
        stop_score=0.56,
        beam_width=96,
        plateau_rounds=16,
        max_children_per_parent=29,
        key_check="exact",
    )

    mask_31_13_31 = mask_from_segments(n, [("B", 0, 124), ("A", 124, 236), ("B", 236, None)])
    run_real_key_recovery_demo(
        title="REAL SOLVE scheduled_stream_lookup: recover segmented P31/P13/P31 key",
        cipher_name="two_period_vigenere",
        cipher_kwargs=dict(
            period_a=13,
            period_b=31,
            alphabet_size=29,
            schedule="mask",
            mask=mask_31_13_31,
        ),
        key_values=key,
        expected_key_len=44,
        stop_score=0.56,
        beam_width=96,
        plateau_rounds=16,
        max_children_per_parent=29,
        key_check="exact",
    )


if __name__ == "__main__":
    main()
