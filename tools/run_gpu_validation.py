"""User-run CUDA provisioning and strict GPU test evidence. No CLI arguments."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rdp.core.config.output_paths import resolve_output_root, path_from
from tools.torch_runtime import provision_torch
from tools.run_validation import build_jobs, run_jobs, Job


def main() -> int:
    if len(sys.argv) != 1:
        raise ValueError("No CLI arguments; configure the launcher's output environment")
    directory = resolve_output_root() / "gpu_validation" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    summary_path = directory / "gpu.json"
    summary = {"status": "running", "tests": "not_run"}
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"GPU evidence: {path_from(directory, ROOT)}", flush=True)

    def run(label, args):
        log_name = label.lower().replace(" ", "_") + ".log"
        print(f"[RUN ] {label}", flush=True)
        with (directory / log_name).open("w", encoding="utf-8") as stream:
            stream.write("command: " + json.dumps(["python", *args[1:]]) + "\n")
            stream.flush()
            process = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True,
                                       encoding="utf-8", errors="replace",
                                       start_new_session=os.name != "nt")
            try:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    stream.write(line)
                    stream.flush()
                if process.wait():
                    raise RuntimeError(f"{label} failed; see {log_name}")
            finally:
                if process.poll() is None:
                    from tools.run_validation import _stop_process_tree
                    _stop_process_tree(process)
                process.stdout.close()

    try:
        run('Install output routing dependency', [sys.executable, '-m', 'pip', 'install',
                                                  'platformdirs>=4.0'])
        summary.update(provision_torch(run, required=True))
        summary['status'] = 'gpu_verified_tests_pending'
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        jobs = [Job('routing_and_provisioning', ('-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                    'tests/tools/test_output_routing.py', 'tests/tools/test_torch_provisioning.py',
                    'tests/tools/test_run_validation.py'), 'pytest_gpu'), *build_jobs('gpu')]
        code, test_dir = run_jobs(jobs, output_root=directory / 'tests')
        summary.update(status='passed' if code == 0 else 'failed',
                       tests=test_dir.relative_to(directory).as_posix())
        return code
    except KeyboardInterrupt:
        summary.update(status='interrupted')
        return 130
    except Exception as exc:
        summary.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        print(f"[FAIL] {exc}", flush=True)
        return 1
    finally:
        summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
