from __future__ import annotations
from tests._helpers.configs import (
    make_logging_cfg,
    make_scorer_cfg,
    make_optimizer_cfg,
    overrides_dict,
)
from rdp.core.types import Device
from tests._helpers.vigenere_case import build_vigenere_known_key_case
from tests.harness import run_roundtrip_case

def run_vigenere_roundtrip_baseline(device: Device, seed: int, beam_width: int, preview: int=48, logging_over: dict | None=None, scorer_over: dict | None=None, optimizer_over: dict | None=None, use_test_key: bool=True):
    """
    Single entrypoint for Tier-A Vigenère tests that:
      - builds the case from the baseline (seed, key length, data),
      - builds dataclass configs from the baseline defaults,
      - applies Tier-A knobs,
      - calls the library runner.
    """
    pt_idx, wli, make_key, encrypt_fn, K, known_key = build_vigenere_known_key_case(
        seed
    )
    logging_cfg = make_logging_cfg({"write_event_log": True})
    scorer_cfg = make_scorer_cfg(scorer_over)
    optimizer_cfg = make_optimizer_cfg('beam', {'beam_width': int(beam_width), **(optimizer_over or {})})
    logging_cfg_overrides = overrides_dict(logging_cfg, extra=logging_over)
    scorer_cfg_overrides = overrides_dict(scorer_cfg, extra=scorer_over)
    optimizer_cfg_overrides = {'name': optimizer_cfg.name, **optimizer_cfg.params}
    if not use_test_key:
        optimizer_cfg_overrides.pop('test_key', None)
    kk, fk, meta = run_roundtrip_case(cipher_name='vigenere', plaintext_idx=pt_idx, wli_data=wli, make_key=make_key, encrypt_fn=encrypt_fn, key_length=K, scorer_cfg_overrides=scorer_cfg_overrides, optimizer_cfg_overrides=optimizer_cfg_overrides, preview=int(preview), seed=int(seed), device=device, logging_cfg_overrides=logging_cfg_overrides, use_test_key=use_test_key)
    return (kk, fk, meta)
