from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.utils.scheduled_stream_lookup_tutorial_utils import (
    key_period13,
    run_real_key_recovery_demo,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    run_real_key_recovery_demo(
        title="REAL SOLVE scheduled_stream_lookup: recover P13 key with generated primes",
        cipher_name="periodic_plus_primes",
        cipher_kwargs=dict(period=13, prime_offset=0, alphabet_size=29),
        key_values=key_period13(),
        expected_key_len=13,
        stop_score=0.56,
    )


if __name__ == "__main__":
    main()
