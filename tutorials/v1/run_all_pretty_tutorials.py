from __future__ import annotations

"""Run all active V1 pretty-print tutorials.

This is the obvious entry point for the all-active pretty tutorial review. The
actual tutorial list and review settings live in ``pretty_print_release_config.toml``
next to this file. There are no CLI switches and no environment-variable control
surface.
"""

from run_pretty_print_release import main


if __name__ == "__main__":
    raise SystemExit(main())
