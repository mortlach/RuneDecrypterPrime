from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli_runner


def test_commit_iteration_outputs_bridge_binding_installed() -> None:
    bridge = getattr(no_wli_runner, "_commit_iteration_outputs_bridge_external", None)
    assert callable(bridge)
    assert callable(getattr(no_wli_runner, "write_pipeline_snapshot_files", None))
    assert callable(getattr(no_wli_runner, "_format_seconds", None))
