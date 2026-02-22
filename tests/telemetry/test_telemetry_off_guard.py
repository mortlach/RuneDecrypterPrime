import pytest

from rune_decrypter_prime.api import RunAPI, by_name, KeySpec, SolverSpec
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.telemetry.pipeline import dump_telemetry

pytestmark = pytest.mark.tier_a


def test_telemetry_off_prevents_dump(tmp_path):
    ct = "ᛗᛁᚩᚾ"
    solver = SolverSpec.ga(pop_size=8, generations=2, seed=123)
    sol = RunAPI.run(
        text=ct,
        cipher=by_name.cipher("vigenere", key_len=3),
        key=KeySpec.repeat(len=3),
        solver=solver,
        encoding_dir=Direction.LTR,
        telemetry_on=False,
    )
    # meta should carry the off flag
    assert getattr(sol, "meta", {}).get("telemetry_off", False) is True
    # dump should be a no-op
    path = dump_telemetry(sol, base_dir=tmp_path)
    assert path == ""
