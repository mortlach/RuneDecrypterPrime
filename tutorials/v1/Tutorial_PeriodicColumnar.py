from __future__ import annotations

"""Periodic columnar multi-scenario tutorial wrapper.

This full tutorial intentionally runs multiple scenario/order combinations. It is
kept as a multi-report walkthrough rather than collapsed into one synthetic
standard summary. For a single-result standard-printer version of this cipher
family, use ``Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py``.
"""

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for path in (_ROOT, _SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_SOURCE = _ROOT / "tutorials" / "old" / "v1_replaced_by_pretty_print" / "Tutorial_PeriodicColumnar.py"


def _load_source_module():
    spec = importlib.util.spec_from_file_location("rdp_periodic_columnar_source_tutorial", _SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load source tutorial: {_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    print("Periodic columnar full multi-scenario tutorial")
    print("mode: compatibility wrapper over the legacy multi-scenario source tutorial")
    print("note: this tutorial emits multiple scenario/order reports; the simple P7 pretty tutorial is the single-result standard-printer version")
    module = _load_source_module()
    module.main()


if __name__ == "__main__":
    main()
