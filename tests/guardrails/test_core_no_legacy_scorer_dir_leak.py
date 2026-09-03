from pathlib import Path
import rdp

def test_core_does_not_emit_scorer_dir_field():
    """
    CORE must not mirror a raw 'scorer.dir' into telemetry (historically leaked 'fwd'/'rev').
    The canonical source of direction for telemetry is the pipeline block.
    """
    root = Path(rdp.__file__).resolve().parent
    se = '\n'.join(
        path.read_text(encoding='utf-8', errors='ignore')
        for path in (root / 'core' / 'engine').glob('*.py')
    )
    assert '["scorer"]["dir"]' not in se and ".get('dir'" not in se, "Remove or normalise any 'scorer.dir' mirrors from core telemetry. Direction should be reported in the pipeline block only."
