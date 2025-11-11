# tests/guardrails/test_engine_no_legacy_default_direction.py
import pytest
from pathlib import Path
import rune_decrypter_prime as rdp

@pytest.mark.xfail(reason="PR9 should remove 'ltr' default from core/solver_engine.py")
def test_solver_engine_no_legacy_fwd_default_string():
    root = Path(rdp.__file__).resolve().parent
    se = (root / "core" / "solver_engine.py").read_text(encoding="utf-8", errors="ignore")
    assert '"ltr"' not in se and "'ltr'" not in se
