from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.runtime_projection_reference_v2 import (
    default_stage_projection_rows,
    project_runtime,
)


def test_runtime_projection_uses_observed_seconds_per_sample() -> None:
    proj = project_runtime(
        stage_name="stageA",
        clean_chunks=10,
        samples_per_chunk=19,
        observed_elapsed_seconds=4510.593,
        observed_samples=38,
    )
    assert proj.total_samples == 190
    assert 118.0 < proj.seconds_per_sample < 119.5
    assert 6.0 < proj.projected_hours < 7.0


def test_default_projection_includes_wide_runs() -> None:
    rows = default_stage_projection_rows(observed_elapsed_seconds=4510.593, observed_samples=38)
    names = {str(row["stage_name"]) for row in rows}
    assert "stageA_10_chunks_current_profile" in names
    assert "wide_500_chunks_109_samples_per_chunk" in names
