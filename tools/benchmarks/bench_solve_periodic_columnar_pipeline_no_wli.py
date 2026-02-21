from __future__ import annotations

"""Legacy entrypoint wrapper.

This script is kept for backward compatibility. The no-WLI runner now lives at:
`tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
"""

from tools.benchmarks.periodic_sub_trans.no_wli.runner import main


if __name__ == "__main__":
    main()
