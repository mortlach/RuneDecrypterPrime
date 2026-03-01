from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parents[4]
    _SRC = _ROOT / "src"
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    if _SRC.exists() and str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

from tools.benchmarks.scoring.span_hamming_nose import bench_span_hamming_nose_suite as suite


# Hardcoded sharding knobs for Process B (RTL pass).
SHARD_STRATEGY = "book_hash_mod"
SHARD_COUNT = 2
SHARD_INDEX = 1

# Keep None to use auto timestamped run dir.
# Set an explicit path only when intentionally resuming.
RUN_DIR_OVERRIDE: str | None = None

# Explicitly pin shard runs to RTL.
FORCE_DIRECTIONS: list[str] | None = ["rtl"]


def main() -> int:
    if FORCE_DIRECTIONS is not None:
        suite.DIRECTIONS = [str(x).strip().lower() for x in FORCE_DIRECTIONS]
    suite.SHARD_STRATEGY = str(SHARD_STRATEGY)
    suite.SHARD_COUNT = int(SHARD_COUNT)
    suite.SHARD_INDEX = int(SHARD_INDEX)
    suite.RUN_DIR_OVERRIDE = RUN_DIR_OVERRIDE
    return int(suite.main())


if __name__ == "__main__":
    raise SystemExit(main())
