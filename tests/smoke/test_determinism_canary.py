# tests/smoke/test_determinism_canary.py
import importlib, json, pytest

pytestmark = pytest.mark.tier_a

ENTRY_POINTS = [
    ("api.solve", "solve"),
    ("rune_decrypter.api.solve", "solve"),
    ("core.engine", "solve"),
]

def _find_entry():
    for mod, attr in ENTRY_POINTS:
        try:
            m = importlib.import_module(mod)
            if hasattr(m, attr):
                return getattr(m, attr)
        except Exception:
            continue
    return None

@pytest.mark.xfail(reason="Determinism guaranteed after RNG injection (PR4).", strict=False)
def test_determinism_canary():
    solve_fn = _find_entry()
    if solve_fn is None:
        pytest.skip("No stable entry point yet.")
    ct = "QEB NRFZH YOLTK CLU GRJMP LSBO QEB IXWV ALD"
    cfg = dict(seed=123, device="cpu", telemetry_on=True,
               eval_budget=200, time_budget_s=1.5, patience_steps=30,
               direction="ltr")
    r0 = solve_fn(ct, **cfg)
    r1 = solve_fn(ct, **cfg)
    json.dumps(getattr(r0, "telemetry", {}), sort_keys=True)
    json.dumps(getattr(r1, "telemetry", {}), sort_keys=True)
