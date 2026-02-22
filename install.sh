#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
else
  echo "Python interpreter not found. Install Python 3.11+ and retry." >&2
  exit 1
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/install.py" "$@"
