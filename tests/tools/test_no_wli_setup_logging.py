from __future__ import annotations

import inspect

from tools.benchmarks.periodic_sub_trans.no_wli.setup_logging import emit_setup_logging


def test_emit_setup_logging_accepts_phasec_fields() -> None:
    params = inspect.signature(emit_setup_logging).parameters
    assert "stage3_phasec_enabled" in params
    assert "stage3_phasec_cfg" in params
    assert "stage3_phasec_start_keys" in params
    assert "stage3_phasec_seed_offset" in params
    assert "stage3_phasec_word_ngram_tiebreak" in params
    assert "stage35_baseline_selector" in params
