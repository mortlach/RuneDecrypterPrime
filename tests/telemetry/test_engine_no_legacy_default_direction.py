# repo/tests/guardrails/test_engine_no_legacy_default_direction.py
import pytest
from pathlib import Path
import rune_decrypter_prime as rdp

pytestmark = pytest.mark.tier_a
def test_solver_engine_no_legacy_fwd_default_string():
    root = Path(rdp.__file__).resolve().parent
    se = (root / "core" / "solver_engine.py").read_text(encoding="utf-8", errors="ignore")
    assert '"fwd"' not in se and "'fwd'" not in se
