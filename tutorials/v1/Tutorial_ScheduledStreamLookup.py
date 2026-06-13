from __future__ import annotations

import sys

from Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence import main as run_p13_sequence
from Tutorial_ScheduledStreamLookup_RealSolve_P13Primes import main as run_p13_primes
from Tutorial_ScheduledStreamLookup_RealSolve_P13P31Overlay import main as run_p13_p31_overlay
from Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented import main as run_p13_p31_segmented

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    run_p13_sequence()
    run_p13_primes()
    run_p13_p31_overlay()
    run_p13_p31_segmented()


if __name__ == "__main__":
    main()
