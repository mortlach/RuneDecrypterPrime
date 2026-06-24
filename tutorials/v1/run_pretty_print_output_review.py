from __future__ import annotations

"""Run the V1 pretty-print tutorials and echo every captured printout.

Use this runner when reviewing whether tutorial printouts are clear and
standardised. It shares the final tutorial list with
``run_pretty_print_release.py`` and changes only the review display policy.
"""

from pathlib import Path

import run_pretty_print_release as release_runner

TITLE = "V1 pretty-print output review"
SHOW_OUTPUT = True
STOP_ON_FIRST_FAILURE = False
WRITE_LOGS = True
OUTPUT_DIR = Path("output/tutorial_pretty_print_output_review_logs")
TAIL_LINES = 80


def main() -> int:
    release_runner.TITLE = TITLE
    release_runner.SHOW_OUTPUT = SHOW_OUTPUT
    release_runner.STOP_ON_FIRST_FAILURE = STOP_ON_FIRST_FAILURE
    release_runner.WRITE_LOGS = WRITE_LOGS
    release_runner.OUTPUT_DIR = OUTPUT_DIR
    release_runner.TAIL_LINES = TAIL_LINES
    return release_runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
