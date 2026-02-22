from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REQUIREMENTS_BY_TARGET = {
    "runner": Path("requirements/targets/runner.txt"),
    "organiser": Path("requirements/targets/organiser.txt"),
    "dev": Path("requirements/targets/dev.txt"),
    "ci-smoke": Path("requirements/targets/ci-smoke.txt"),
}
DEFAULT_CANARY_CONFIG = Path("tools/benchmarks/community/examples/canary_campaign_config_v1_1.json")
DEFAULT_PROFILE_CATALOG = Path("tools/benchmarks/community/profile_catalog_v1_1.json")
DEFAULT_CAMPAIGN_CONFIG = Path("tools/benchmarks/community/examples/campaign_config_v1_1.json")
SETUP_AND_PREFLIGHT_SCRIPT = Path("tools/benchmarks/community/setup_and_preflight.py")
GENERATE_MANIFEST_SCRIPT = Path("tools/benchmarks/community/generate_manifest.py")
SHARD_MANIFEST_SCRIPT = Path("tools/benchmarks/community/shard_manifest.py")
RUN_SHARD_SCRIPT = Path("tools/benchmarks/community/run_shard.py")
CANARY_OUTPUT_ROOT = Path("output/tools/benchmarks/community/canary")


@dataclass(frozen=True)
class BootstrapResult:
    repo_root: Path
    python_executable: Path
    target: str
    requirements_file: Path
    setup_preflight_ran: bool
    canary_ran: bool


def _log(msg: str) -> None:
    print(f"[bootstrap] {msg}", flush=True)


def _cmd_display(cmd: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(cmd)
    return " ".join(shlex.quote(part) for part in cmd)


def _run(cmd: list[str], *, cwd: Path) -> None:
    _log(f"$ {_cmd_display(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {_cmd_display(cmd)}")


def _resolve_repo_root(repo_root: Path) -> Path:
    root = repo_root.resolve()
    sentinel = root / SETUP_AND_PREFLIGHT_SCRIPT
    if not sentinel.exists():
        raise FileNotFoundError(f"repo root does not contain {SETUP_AND_PREFLIGHT_SCRIPT}: {root}")
    return root


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _ensure_python_for_bootstrap(
    *,
    repo_root: Path,
    use_venv: bool,
    venv_relpath: str,
    base_python: str,
    recreate_venv: bool,
) -> Path:
    if not use_venv:
        return Path(base_python).resolve()

    venv_dir = (repo_root / venv_relpath).resolve()
    py_path = _venv_python(venv_dir)
    if recreate_venv and venv_dir.exists():
        _log(f"Removing existing venv: {venv_dir}")
        shutil.rmtree(venv_dir)
    if not py_path.exists():
        _log(f"Creating venv: {venv_dir}")
        _run([base_python, "-m", "venv", str(venv_dir)], cwd=repo_root)
    if not py_path.exists():
        raise FileNotFoundError(f"venv python not found after creation: {py_path}")
    return py_path.resolve()


def _resolve_requirements_file(
    *,
    repo_root: Path,
    target: str,
    requirements_override: str | None,
) -> Path:
    if requirements_override:
        req = Path(requirements_override)
        if not req.is_absolute():
            req = repo_root / req
        return req.resolve()
    rel = DEFAULT_REQUIREMENTS_BY_TARGET[target]
    return (repo_root / rel).resolve()


def _install_dependencies(
    *,
    repo_root: Path,
    python_executable: Path,
    requirements_file: Path,
    skip_pip_upgrade: bool,
    skip_editable_install: bool,
) -> None:
    if not requirements_file.exists():
        raise FileNotFoundError(f"requirements file not found: {requirements_file}")

    if not skip_pip_upgrade:
        _run([str(python_executable), "-m", "pip", "install", "--upgrade", "pip"], cwd=repo_root)
    _run([str(python_executable), "-m", "pip", "install", "-r", str(requirements_file)], cwd=repo_root)
    if not skip_editable_install:
        _run([str(python_executable), "-m", "pip", "install", "-e", "."], cwd=repo_root)


def _run_setup_and_preflight(
    *,
    repo_root: Path,
    python_executable: Path,
    skip_fastlm_build: bool,
) -> None:
    script = (repo_root / SETUP_AND_PREFLIGHT_SCRIPT).resolve()
    cmd = [str(python_executable), str(script), "--repo-root", str(repo_root)]
    if skip_fastlm_build:
        cmd.append("--skip-fastlm-build")
    _run(cmd, cwd=repo_root)


def _read_json(path: Path) -> Mapping[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object at {path}")
    return data


def _run_canary(
    *,
    repo_root: Path,
    python_executable: Path,
    canary_config: Path,
    profile_catalog: Path,
    runner_id: str,
    max_jobs: int | None,
) -> None:
    canary_root = (repo_root / CANARY_OUTPUT_ROOT).resolve()
    canary_root.mkdir(parents=True, exist_ok=True)
    shards_dir = canary_root / "shards"
    manifest_path = canary_root / "manifest_canary.jsonl"
    manifest_summary_path = canary_root / "manifest_canary.summary.json"
    shard_index_path = shards_dir / "shard_index.json"
    runner_cfg_path = canary_root / "runner_config_local.generated.json"

    _run(
        [
            str(python_executable),
            str((repo_root / GENERATE_MANIFEST_SCRIPT).resolve()),
            "--campaign-config",
            str(canary_config),
            "--profile-catalog",
            str(profile_catalog),
            "--output",
            str(manifest_path),
            "--summary-output",
            str(manifest_summary_path),
        ],
        cwd=repo_root,
    )

    _run(
        [
            str(python_executable),
            str((repo_root / SHARD_MANIFEST_SCRIPT).resolve()),
            "--manifest",
            str(manifest_path),
            "--output-dir",
            str(shards_dir),
            "--num-shards",
            "1",
            "--basename",
            "canary_shard",
            "--index-output",
            str(shard_index_path),
        ],
        cwd=repo_root,
    )

    shard_index = _read_json(shard_index_path)
    shards = shard_index.get("shards")
    if not isinstance(shards, list) or not shards:
        raise RuntimeError(f"canary sharding produced no shard files: {shard_index_path}")
    first = shards[0]
    if not isinstance(first, dict) or "path" not in first:
        raise RuntimeError(f"invalid shard index entry in {shard_index_path}")
    shard_path = Path(str(first["path"])).resolve()

    runner_cfg = {
        "runner_id": runner_id,
        "shard_path": str(shard_path),
        "output_root": str(canary_root),
        "resume": True,
        "max_jobs": max_jobs,
    }
    runner_cfg_path.write_text(json.dumps(runner_cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _run(
        [
            str(python_executable),
            str((repo_root / RUN_SHARD_SCRIPT).resolve()),
            "--runner-config",
            str(runner_cfg_path),
            "--campaign-config",
            str(canary_config),
            "--profile-catalog",
            str(profile_catalog),
        ],
        cwd=repo_root,
    )


def run_bootstrap(
    *,
    repo_root: Path,
    target: str,
    requirements_override: str | None,
    use_venv: bool,
    venv_relpath: str,
    base_python: str,
    recreate_venv: bool,
    skip_dependency_install: bool,
    skip_pip_upgrade: bool,
    skip_editable_install: bool,
    skip_preflight: bool,
    skip_fastlm_build: bool,
    run_canary: bool,
    canary_runner_id: str,
    canary_max_jobs: int | None,
    campaign_config: Path,
    canary_config: Path,
    profile_catalog: Path,
) -> BootstrapResult:
    resolved_root = _resolve_repo_root(repo_root)
    resolved_python = _ensure_python_for_bootstrap(
        repo_root=resolved_root,
        use_venv=use_venv,
        venv_relpath=venv_relpath,
        base_python=base_python,
        recreate_venv=recreate_venv,
    )
    requirements_file = _resolve_requirements_file(
        repo_root=resolved_root,
        target=target,
        requirements_override=requirements_override,
    )

    if run_canary and skip_preflight:
        raise ValueError("--run-canary requires preflight; remove --skip-preflight")

    resolved_campaign = campaign_config if campaign_config.is_absolute() else (resolved_root / campaign_config)
    resolved_canary = canary_config if canary_config.is_absolute() else (resolved_root / canary_config)
    resolved_profiles = profile_catalog if profile_catalog.is_absolute() else (resolved_root / profile_catalog)

    _log(f"repo_root={resolved_root}")
    _log(f"target={target}")
    _log(f"python={resolved_python}")
    _log(f"requirements={requirements_file}")
    _log(f"campaign_config={resolved_campaign.resolve()}")
    _log(f"canary_config={resolved_canary.resolve()}")
    _log(f"profile_catalog={resolved_profiles.resolve()}")

    if not skip_dependency_install:
        _install_dependencies(
            repo_root=resolved_root,
            python_executable=resolved_python,
            requirements_file=requirements_file,
            skip_pip_upgrade=skip_pip_upgrade,
            skip_editable_install=skip_editable_install,
        )
    else:
        _log("Skipping dependency install (--skip-dependency-install)")

    setup_preflight_ran = False
    if not skip_preflight:
        _run_setup_and_preflight(
            repo_root=resolved_root,
            python_executable=resolved_python,
            skip_fastlm_build=skip_fastlm_build,
        )
        setup_preflight_ran = True
    else:
        _log("Skipping setup+preflight (--skip-preflight)")

    canary_ran = False
    if run_canary:
        _run_canary(
            repo_root=resolved_root,
            python_executable=resolved_python,
            canary_config=resolved_canary.resolve(),
            profile_catalog=resolved_profiles.resolve(),
            runner_id=canary_runner_id,
            max_jobs=canary_max_jobs,
        )
        canary_ran = True

    return BootstrapResult(
        repo_root=resolved_root,
        python_executable=resolved_python,
        target=target,
        requirements_file=requirements_file,
        setup_preflight_ran=setup_preflight_ran,
        canary_ran=canary_ran,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cross-platform bootstrap for RDP community benchmark environments.",
    )
    parser.add_argument(
        "--target",
        choices=tuple(DEFAULT_REQUIREMENTS_BY_TARGET.keys()),
        default="runner",
        help="install target profile (default: runner)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help=f"repository root (default: {REPO_ROOT})",
    )
    parser.add_argument(
        "--requirements",
        type=str,
        default=None,
        help="optional requirements file override",
    )
    parser.add_argument(
        "--python",
        type=str,
        default=sys.executable,
        help="base python used for venv creation (default: current interpreter)",
    )
    parser.add_argument(
        "--venv",
        type=str,
        default=".venv",
        help="venv path relative to repo root when venv mode is enabled (default: .venv)",
    )
    parser.add_argument(
        "--no-venv",
        action="store_true",
        help="use the current interpreter instead of creating/using a venv",
    )
    parser.add_argument(
        "--recreate-venv",
        action="store_true",
        help="delete and recreate venv before installing",
    )
    parser.add_argument(
        "--skip-dependency-install",
        action="store_true",
        help="skip pip install steps",
    )
    parser.add_argument(
        "--skip-pip-upgrade",
        action="store_true",
        help="skip `pip install --upgrade pip`",
    )
    parser.add_argument(
        "--skip-editable-install",
        action="store_true",
        help="skip `pip install -e .`",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="skip setup_and_preflight.py execution",
    )
    parser.add_argument(
        "--skip-fastlm-build",
        action="store_true",
        help="pass --skip-fastlm-build into setup_and_preflight.py",
    )
    parser.add_argument(
        "--run-canary",
        action="store_true",
        help="run canary manifest/shard/runner after setup+preflight",
    )
    parser.add_argument(
        "--canary-runner-id",
        type=str,
        default="bootstrap_local",
        help="runner_id to use for generated canary runner config",
    )
    parser.add_argument(
        "--canary-max-jobs",
        type=int,
        default=None,
        help="optional max_jobs for canary runner config",
    )
    parser.add_argument(
        "--campaign-config",
        type=Path,
        default=DEFAULT_CAMPAIGN_CONFIG,
        help=f"campaign config path (default: {DEFAULT_CAMPAIGN_CONFIG})",
    )
    parser.add_argument(
        "--canary-config",
        type=Path,
        default=DEFAULT_CANARY_CONFIG,
        help=f"canary campaign config path (default: {DEFAULT_CANARY_CONFIG})",
    )
    parser.add_argument(
        "--profile-catalog",
        type=Path,
        default=DEFAULT_PROFILE_CATALOG,
        help=f"profile catalog path (default: {DEFAULT_PROFILE_CATALOG})",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = run_bootstrap(
        repo_root=args.repo_root,
        target=str(args.target),
        requirements_override=args.requirements,
        use_venv=not bool(args.no_venv),
        venv_relpath=str(args.venv),
        base_python=str(args.python),
        recreate_venv=bool(args.recreate_venv),
        skip_dependency_install=bool(args.skip_dependency_install),
        skip_pip_upgrade=bool(args.skip_pip_upgrade),
        skip_editable_install=bool(args.skip_editable_install),
        skip_preflight=bool(args.skip_preflight),
        skip_fastlm_build=bool(args.skip_fastlm_build),
        run_canary=bool(args.run_canary),
        canary_runner_id=str(args.canary_runner_id),
        canary_max_jobs=args.canary_max_jobs,
        campaign_config=args.campaign_config,
        canary_config=args.canary_config,
        profile_catalog=args.profile_catalog,
    )
    _log("Bootstrap completed.")
    _log(f"target={result.target}")
    _log(f"python={result.python_executable}")
    _log(f"requirements={result.requirements_file}")
    _log(f"setup_preflight_ran={result.setup_preflight_ran}")
    _log(f"canary_ran={result.canary_ran}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
