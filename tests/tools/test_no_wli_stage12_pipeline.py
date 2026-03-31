from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.stage12_pipeline import (
    run_stage12_pipeline,
)


pytestmark = pytest.mark.tier_a


def _base_kwargs():
    return dict(
        tier=SimpleNamespace(name="fixture_fixture_001_p9_c3_l1000", period=9, columns=3),
        text_id=0,
        key_seed=211,
        ct_idx=np.asarray([1, 2, 3], dtype=np.uint8),
        pt_idx=np.asarray([1, 2, 3], dtype=np.uint8),
        true_sub=np.asarray([0, 1, 2], dtype=np.int16),
        sub_len=3,
        wli=[],
        direction="ltr",
        scorer_stage1={},
        scorer_stage1_runtime=object(),
        sub_cipher=object(),
        scorer_stage2={},
        scorer_stage2_runtime=object(),
        scorer_stage2_pass1_primary_runtime=None,
        scorer_stage2_pass1_fallback_runtime=None,
        full_cipher=object(),
        scorer_stage2_judge_cfg={},
        scorer_stage2_judge_runtime=object(),
        scorer_full_runtime=object(),
        oracle_assist_selection_effective=False,
        mark_oracle_decision_use_fn=lambda: None,
        stages=[],
    )


def _valid_stage1(**overrides):
    payload = dict(
        sub_candidates=[[0, 1, 2]],
        sub_key_match=0.125,
        stage1_best_score=-2.5,
        evals=17,
    )
    payload.update(overrides)
    return payload


def _valid_stage2_search(**overrides):
    payload = dict(
        best2_match=0.25,
        best2_score=-4.0,
        best2_key=[0, 1, 2],
        best2_pt=[1, 2, 3],
        best2_preview="ABC",
        stage2_evals_total=33,
        stage2_archive={(0, 1, 2): {"key": [0, 1, 2], "plaintext": [1, 2, 3]}},
        stage2_archive_keep=8,
        stage2_promote_top=4,
        stage2_entry_score=-4.0,
        stage2_continue_to_gate=False,
        stage2_continue_stop_reason="",
    )
    payload.update(overrides)
    return payload


def _valid_stage2_finalize(**overrides):
    payload = dict(
        best2_match=0.25,
        best2_score=-4.0,
        best2_key=[0, 1, 2],
        best2_pt=[1, 2, 3],
        best2_preview="ABC",
        stage2_ranked=[],
        stage2_promoted=[],
        stage2_entry_score=-4.0,
        stage2_entry_score_judge=-4.0,
        stage2_score_match_spearman=0.0,
        stage2_stage3_space_match=True,
        stage2_topk_payload=[],
        stage2_topk_has_best_match=True,
    )
    payload.update(overrides)
    return payload


def test_stage12_pipeline_happy_path_returns_expected_payload() -> None:
    out = run_stage12_pipeline(
        **_base_kwargs(),
        run_stage1_substitution_fn=lambda **_: _valid_stage1(),
        run_stage2_search_fn=lambda **_: _valid_stage2_search(),
        finalize_stage2_archive_fn=lambda **_: _valid_stage2_finalize(),
    )

    assert out["sub_key_match"] == pytest.approx(0.125)
    assert out["stage1_best_score"] == pytest.approx(-2.5)
    assert out["ev1"] == 17
    assert out["best2_key"] == [0, 1, 2]
    assert out["stage2_evals_total"] == 33
    assert out["stage2_topk_has_best_match"] is True


def test_stage12_pipeline_rejects_missing_stage1_keys() -> None:
    def _bad_stage1(**_):
        payload = _valid_stage1()
        del payload["evals"]
        return payload

    with pytest.raises(KeyError, match="run_stage1_substitution_fn missing required keys: evals"):
        run_stage12_pipeline(
            **_base_kwargs(),
            run_stage1_substitution_fn=_bad_stage1,
            run_stage2_search_fn=lambda **_: _valid_stage2_search(),
            finalize_stage2_archive_fn=lambda **_: _valid_stage2_finalize(),
        )


def test_stage12_pipeline_rejects_missing_stage2_search_keys() -> None:
    def _bad_stage2_search(**_):
        payload = _valid_stage2_search()
        del payload["stage2_archive"]
        return payload

    with pytest.raises(
        KeyError,
        match="run_stage2_search_fn missing required keys: stage2_archive",
    ):
        run_stage12_pipeline(
            **_base_kwargs(),
            run_stage1_substitution_fn=lambda **_: _valid_stage1(),
            run_stage2_search_fn=_bad_stage2_search,
            finalize_stage2_archive_fn=lambda **_: _valid_stage2_finalize(),
        )


def test_stage12_pipeline_rejects_wrong_stage2_search_archive_type() -> None:
    with pytest.raises(
        TypeError,
        match="run_stage2_search_fn.stage2_archive must be a mapping",
    ):
        run_stage12_pipeline(
            **_base_kwargs(),
            run_stage1_substitution_fn=lambda **_: _valid_stage1(),
            run_stage2_search_fn=lambda **_: _valid_stage2_search(stage2_archive=[]),
            finalize_stage2_archive_fn=lambda **_: _valid_stage2_finalize(),
        )


def test_stage12_pipeline_rejects_missing_stage2_finalize_keys() -> None:
    def _bad_stage2_finalize(**_):
        payload = _valid_stage2_finalize()
        del payload["stage2_promoted"]
        return payload

    with pytest.raises(
        KeyError,
        match="finalize_stage2_archive_fn missing required keys: stage2_promoted",
    ):
        run_stage12_pipeline(
            **_base_kwargs(),
            run_stage1_substitution_fn=lambda **_: _valid_stage1(),
            run_stage2_search_fn=lambda **_: _valid_stage2_search(),
            finalize_stage2_archive_fn=_bad_stage2_finalize,
        )
