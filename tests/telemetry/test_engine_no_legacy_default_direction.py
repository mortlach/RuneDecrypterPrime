import pytest
from pathlib import Path
import rdp
pytestmark = pytest.mark.tier_a

def test_solver_engine_no_legacy_fwd_default_string():
    root = Path(rdp.__file__).resolve().parent
    se = '\n'.join(
        path.read_text(encoding='utf-8', errors='ignore')
        for path in (root / 'core' / 'engine').glob('*.py')
    )
    assert '"fwd"' not in se and "'fwd'" not in se
