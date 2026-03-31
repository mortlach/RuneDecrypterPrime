from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod
from tools.benchmarks.periodic_sub_trans.no_wli.stage35_candidate_archive import (
    build_stage35_seed_archive,
)


def _repo_rel(path: Path, *, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def write_resume_handoff_artifacts(
    *,
    run_dir: Path,
    root: Path,
    artifact_path: Path,
    artifact_payload: Mapping[str, Any],
    run_config_path: Path,
    write_json_fn: Callable[[Path, dict[str, Any]], None],
    live_stage2_resume: Mapping[str, Any] | None = None,
    live_stage3_prep: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    bundle_dir = run_dir / "resume_handoffs" / str(artifact_path.stem)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = dict(
        artifact_relpath=_repo_rel(artifact_path, root=root),
        run_config_relpath=_repo_rel(run_config_path, root=root),
        bundle_dir_relpath=_repo_rel(bundle_dir, root=root),
        stage2_to_stage3=dict(saved=0, error=""),
        stage3_to_stage35=dict(saved=0, error=""),
    )

    try:
        if live_stage2_resume is not None and live_stage3_prep is not None:
            stage2_resume = resume_mod._coerce_stage2_resume_inputs(
                dict(live_stage2_resume)
            )
            stage3_prep = dict(live_stage3_prep)
            source = "live_stage3_pipeline"
        else:
            prep = resume_mod.prepare_stage3_resume_inputs(
                dict(artifact_payload),
                dict(run_config),
            )
            stage2_resume = prep["stage2_resume"]
            stage3_prep = dict(prep["stage3_prep"])
            source = str(prep.get("resume_source", "reconstructed_stage2_topk"))
        write_json_fn(bundle_dir / "stage2_resume.json", dict(stage2_resume.__dict__))
        write_json_fn(bundle_dir / "stage3_prep.json", dict(stage3_prep))
        manifest["stage2_to_stage3"] = dict(
            saved=1,
            source=str(source),
            stage2_topk_row_count=int(stage2_resume.stage2_topk_row_count),
            stage2_promoted_from_topk_count=int(stage2_resume.stage2_promoted_from_topk_count),
            stage3_init3_count=int(len(list(stage3_prep.get("init3", []) or []))),
            error="",
        )
    except Exception as exc:
        manifest["stage2_to_stage3"] = dict(saved=0, error=str(exc))

    try:
        seed_archive = build_stage35_seed_archive(dict(artifact_payload))
        write_json_fn(bundle_dir / "stage35_seed_archive.json", dict(seed_archive))
        manifest["stage3_to_stage35"] = dict(
            saved=1,
            seed_count=int(len(list(seed_archive.get("seed_rows", []) or []))),
            frozen_tail_len=int(len(list(seed_archive.get("frozen_tail", []) or []))),
            tail_mismatch_count=int(seed_archive.get("tail_mismatch_count", 0) or 0),
            error="",
        )
    except Exception as exc:
        manifest["stage3_to_stage35"] = dict(saved=0, error=str(exc))

    write_json_fn(bundle_dir / "manifest.json", manifest)
    return dict(manifest)
