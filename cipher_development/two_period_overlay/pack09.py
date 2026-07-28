from __future__ import annotations

"""IDE-friendly WP6 Pack 09 one-word d30 runner."""

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cipher_development.two_period_overlay.experiment_e import (
    contract_preflight,
    planned_runtime,
    run_p13_p31_one_word_d30_panel,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_PREFLIGHT = True
RUN_SCIENCE_PANEL = True


def main() -> int:
    print("RDP WP6 Pack 09 — P13/P31 one-word d30 discovery panel")
    print("=" * 66)
    print(json.dumps(planned_runtime(), indent=2, sort_keys=True))

    if RUN_PREFLIGHT:
        print("\nContract preflight")
        print("------------------")
        print(json.dumps(contract_preflight(REPO_ROOT), indent=2, sort_keys=True))

    if RUN_SCIENCE_PANEL:
        print("\nScientific execution")
        print("--------------------")
        result = run_p13_p31_one_word_d30_panel(REPO_ROOT)
        print(f"result: {result}")
    else:
        print("\nRUN_SCIENCE_PANEL is False; no scientific run was started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
