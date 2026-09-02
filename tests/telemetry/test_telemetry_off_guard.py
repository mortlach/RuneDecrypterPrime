from rdp import api
import pytest
from rdp.telemetry.pipeline import dump_telemetry
pytestmark = pytest.mark.tier_a

def test_telemetry_off_prevents_dump(tmp_path):
    ct = "ᛗᛁᚩᚾ"
    solver = api.SolverSpec.genetic_algorithm(
        population_size=8, generations=2, seed=123
    )
    sol = api.run(
        api.RunSpec(
            problem_input=api.RawTextInput(text=ct),
            cipher=api.CipherSpec.vigenere(alphabet_size=29),
            key_space=api.KeySpec.repeating(length=3),
            solver=solver,
            scoring=api.ScoringConfig(),
            telemetry_enabled=False,
            text_direction=api.TextDirection.LEFT_TO_RIGHT,
        )
    )
    assert dict(sol.telemetry) == {"telemetry_off": True}
    path = dump_telemetry(sol, base_dir=tmp_path)
    assert path == ''
