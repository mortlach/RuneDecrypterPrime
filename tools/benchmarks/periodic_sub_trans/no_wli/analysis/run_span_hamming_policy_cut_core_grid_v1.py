from __future__ import annotations

"""
Report-only deduplicated span-Hamming policy-cut core grid.

This runner avoids known duplicate work from the full policy-cut wrapper:

- `normal_selected` is equivalent to `raw_selected` in the restored assets.
- `strict_all`, `normal_all`, and `broad_all` are equivalent to `raw_all`
  because `require_selected=False` ignores the policy selected column.
- `hd3` is deliberately split out to a separate slow-path follow-up.
- exact `hd0` uses one cap because prior S1f results showed identical exact
  feature rows across caps.
"""

from collections.abc import Sequence

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    calibrate_span_hamming_full_space_v1 as calibration,
)


calibration.RUN_LABEL = "span_hamming_policy_cut_core_grid_v1"
calibration.OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_policy_cut_core_grid_v1"
)
calibration.OUTPUT_DIR = calibration.REPO_ROOT / calibration.OUTPUT_DIR_REL

calibration.TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 0
calibration.PROGRESS_EVERY_CANDIDATES = 100
calibration.TIMING_SAMPLE_TOKEN_LIMIT = 12
calibration.PYTHON_PARITY_SPOT_CHECK = True
calibration.PYTHON_PARITY_TOKEN_LIMIT = 4
calibration.PYTHON_PARITY_CONFIG_LIMIT = 3


DICTIONARY_SPECS = (
    dict(dictionary_id="raw_selected", wordlist_rel="assets/hamming_raw_1g", require_selected=True),
    dict(dictionary_id="raw_all", wordlist_rel="assets/hamming_raw_1g", require_selected=False),
    dict(
        dictionary_id="strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="broad_selected",
        wordlist_rel="assets/hamming_dictionary_policies/broad/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="research_selected",
        wordlist_rel="assets/hamming_dictionary_policies/research/hamming_raw_1g",
        require_selected=True,
    ),
)

TEMPLATE_CAP_SPECS: tuple[tuple[dict[str, int | str], Sequence[int]], ...] = (
    (dict(template_id="len1_14_hd0_exact", len_min=1, len_max=14, max_hd=0), (256,)),
    (dict(template_id="len1_14_hd1", len_min=1, len_max=14, max_hd=1), (256, 512, 1024)),
    (dict(template_id="len1_14_hd2", len_min=1, len_max=14, max_hd=2), (256, 512, 1024)),
    (dict(template_id="len3_14_hd2_s1b_shape", len_min=3, len_max=14, max_hd=2), (256, 512, 1024)),
    (dict(template_id="len5_14_hd2_longer", len_min=5, len_max=14, max_hd=2), (256, 512, 1024)),
    (dict(template_id="len8_14_hd2_long_signal", len_min=8, len_max=14, max_hd=2), (256, 512, 1024)),
    (dict(template_id="len10_14_hd2_very_long_signal", len_min=10, len_max=14, max_hd=2), (256, 512, 1024)),
    (dict(template_id="len1_4_hd2_short_noise", len_min=1, len_max=4, max_hd=2), (256, 512, 1024)),
)


def _core_config_specs() -> list[calibration.SpanConfigSpec]:
    out: list[calibration.SpanConfigSpec] = []
    for dict_row in DICTIONARY_SPECS:
        dict_spec = calibration.DictionarySpec(**dict_row)
        for template_row, caps in TEMPLATE_CAP_SPECS:
            template = calibration.SpanTemplateSpec(**template_row)
            for cap in caps:
                config_id = f"{dict_spec.dictionary_id}__{template.template_id}__cap{cap}"
                out.append(
                    calibration.SpanConfigSpec(
                        config_id=config_id,
                        dictionary_id=dict_spec.dictionary_id,
                        wordlist_rel=dict_spec.wordlist_rel,
                        require_selected=dict_spec.require_selected,
                        template_id=template.template_id,
                        len_min=template.len_min,
                        len_max=template.len_max,
                        max_hd=template.max_hd,
                        max_candidates_per_window=int(cap),
                    )
                )
    return out


calibration._config_specs = _core_config_specs


def main() -> None:
    calibration.main()


if __name__ == "__main__":
    main()
