from __future__ import annotations

from typing import get_type_hints

from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import ECDFCache
from rune_decrypter_prime.scoring.language_model.paths import LmIndex, load_index, resolve_lm_root


def test_v1_language_model_asset_contract_has_structured_entry_points() -> None:
    assert callable(resolve_lm_root)
    assert callable(load_index)
    assert get_type_hints(LmIndex)["models"] is dict


def test_v1_ecdf_asset_contract_exposes_status_metadata_methods() -> None:
    required = {
        "asset_id",
        "load",
        "meta",
        "meta_hash",
        "interp_dtype",
        "validate_clamp_range",
    }

    assert required <= set(ECDFCache.__dict__)


def test_v1_ecdf_asset_contract_does_not_require_a_new_registry_layer() -> None:
    # D7 keeps the asset contract small: LM root/index resolution plus ECDFCache
    # validation/status methods are the source of truth for V1 LM/ECDF assets.
    assert ECDFCache.__module__ == "rune_decrypter_prime.scoring.language_model.language_model_prime_runtime"
    assert resolve_lm_root.__module__ == "rune_decrypter_prime.scoring.language_model.paths"
