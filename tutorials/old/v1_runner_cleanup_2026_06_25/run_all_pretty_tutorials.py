from __future__ import annotations

"""Run all active V1 pretty-print tutorials.

This is an alias for the pretty-print release runner. The tutorial list and
review settings live as constants near the top of ``run_tutorials.py``.
There are no CLI switches, environment-variable controls, or separate config
files for normal tutorial control.
"""

from run_pretty_print_release import main


if __name__ == "__main__":
    raise SystemExit(main())
