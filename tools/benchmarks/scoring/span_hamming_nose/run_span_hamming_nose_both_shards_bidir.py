from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SHARD0_SCRIPT = SCRIPT_DIR / "run_span_hamming_nose_shard0_bidir.py"
SHARD1_SCRIPT = SCRIPT_DIR / "run_span_hamming_nose_shard1_bidir.py"


def main() -> int:
    procs = [
        subprocess.Popen([sys.executable, str(SHARD0_SCRIPT)], cwd=str(SCRIPT_DIR)),
        subprocess.Popen([sys.executable, str(SHARD1_SCRIPT)], cwd=str(SCRIPT_DIR)),
    ]
    rc0 = int(procs[0].wait())
    rc1 = int(procs[1].wait())
    if rc0 != 0 or rc1 != 0:
        print(
            f"[span_hamming_nose] dual-shard launcher failed rc_shard0={rc0} rc_shard1={rc1}",
            flush=True,
        )
        return 1
    print("[span_hamming_nose] dual-shard launcher complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

