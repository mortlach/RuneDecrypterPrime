from __future__ import annotations

"""No-WLI benchmark launcher: period=5, columns=1..5 using A34->M34->B34."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.benchmarks.periodic_sub_trans.no_wli.runs import (
    run_focus_p5_c1_c5 as base_run,
)


def main() -> None:
    base_run.NO_WLI_PROFILE_ID = "no_wli_a34_m34_b34_v1"
    base_run.main()


if __name__ == "__main__":
    main()

