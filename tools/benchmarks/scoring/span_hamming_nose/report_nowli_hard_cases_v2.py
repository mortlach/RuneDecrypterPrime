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


import tools.benchmarks.scoring.span_hamming_nose.report_nowli_hard_cases_v1 as report_v1


report_v1.DATASET_JSON = Path("tests/scoring/span_hamming/data/nowli_hard_cases_v2.json")
report_v1.RUN_LABEL = "report_nowli_hard_cases_v2"


if __name__ == "__main__":
    report_v1.main()
