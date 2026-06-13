# todo add a fastpath helper ovel to test these things
# """
# Why: Telemetry must expose the pipeline block with canonical 'ltr'/'rtl' strings.
# Proves: A minimal API-run surfaces telemetry with pipeline.text_encoding_direction ∈ {'ltr','rtl'}.
# Note: If your public API is class-based, adapt the call below (same assertions apply).
# """
# import json
#
# from rune_decrypter_prime.core.types import Direction
# from rune_decrypter_prime.api import api as api_mod  # module is present in repo
#
# def test_pipeline_block_direction_is_canonical(monkeypatch):
#     # Use the smallest callable public entry you expose in api/api.py.
#     # If your API exposes run_once / solve / Runner(...).run(), call that here.
#     solve = getattr(api_mod, "solve", None) or getattr(api_mod, "run_once", None)
#     assert callable(solve), "Expose a callable entry in api/api.py (solve(...) or run_once(...))."
#
#     # Minimal, deterministic call — adapt arg names to your API if needed:
#     res = solve(
#         ciphertext="ABC",                 # tiny input; exact content isn't important here
#         direction=Direction.LTR,         # pass Enum at API edge
#         telemetry_on=True,
#         eval_budget=1,                   # keep it tiny
#         seed=123,
#     )
#     # Expect result/meta to contain telemetry; adapt if your API returns a (result, meta) tuple.
#     meta = getattr(res, "meta", None) or getattr(res, "telemetry", None) or {}
#     tel = meta if isinstance(meta, dict) else getattr(meta, "to_dict", lambda: {})()
#
#     text = json.dumps(tel)
#     assert '"pipeline"' in text, f"telemetry missing pipeline block: {text}"
#     assert '"text_encoding_direction": "ltr"' in text, f"direction must be canonical: {text}"
#     assert "fwd" not in text and "rev" not in text, "legacy tokens must not leak into telemetry"
