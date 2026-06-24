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
    sample_sequence,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    sequence = sample_sequence(64)

    run_real_key_recovery_demo(
        title="REAL SOLVE scheduled_stream_lookup: recover P13 key with supplied sequence",
        cipher_name="scheduled_stream_lookup",
        cipher_kwargs=dict(
            streams=[
                {"name": "A", "kind": "periodic", "period": 13},
                {"name": "S", "kind": "sequence", "values": sequence},
            ],
            schedule="overlay",
            operation="add",
            alphabet_size=29,
        ),
        key_values=key_period13(),
        expected_key_len=13,
        stop_score=0.56,
    )


if __name__ == "__main__":
    main()
