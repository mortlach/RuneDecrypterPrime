"""Detect, provision and verify NVIDIA Torch. No CLI options; installer-owned policy."""
from __future__ import annotations
import csv
import json
import platform
import shutil
import subprocess
import sys

# Official wheels: https://pytorch.org/get-started/previous-versions/
TORCH_VERSION = "2.13.0"
# Conservative toolkit-release driver floors, rather than relying on minor compatibility.
# https://docs.nvidia.com/cuda/archive/12.6.0/cuda-toolkit-release-notes/index.html
DRIVER_FLOORS = {"Windows": (560, 76), "Linux": (560, 28, 3)}


def detect_gpus() -> list[dict]:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return []
    result = subprocess.run([executable, "--query-gpu=name,driver_version,compute_cap",
                             "--format=csv,noheader,nounits"], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("nvidia-smi failed; repair the NVIDIA driver before GPU provisioning: "
                           + result.stderr.strip())
    return [dict(name=row[0].strip(), driver=row[1].strip(), capability=row[2].strip())
            for row in csv.reader(result.stdout.splitlines()) if row]


def select_wheel(gpus: list[dict], system: str | None = None) -> str:
    system = system or platform.system()
    if system not in DRIVER_FLOORS or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("Automatic CUDA provisioning supports Windows/Linux x86-64")
    capabilities = [tuple(map(int, gpu["capability"].split("."))) for gpu in gpus]
    if not capabilities or min(capabilities) < (7, 5):
        raise RuntimeError("GPU architecture requires a manually selected compatible Torch build")
    index = "cu130" if max(capabilities) >= (10, 0) else "cu126"
    floor = (580, 0) if index == "cu130" else DRIVER_FLOORS[system]
    if any(tuple(map(int, gpu["driver"].split("."))) < floor for gpu in gpus):
        raise RuntimeError(f"NVIDIA driver is too old for {index}; update the driver and retry")
    return index


PROBE = r'''import json, torch
assert torch.version.cuda is not None, "Installed Torch is CPU-only"
assert torch.cuda.is_available(), "Torch cannot access CUDA"
devices = []
for index in range(torch.cuda.device_count()):
    device = torch.device("cuda", index)
    x = torch.arange(16, dtype=torch.float32, device=device).reshape(4, 4)
    actual = x @ x.T
    torch.cuda.synchronize(device)
    expected = x.cpu() @ x.cpu().T
    assert torch.equal(actual.cpu(), expected), "CUDA arithmetic verification failed"
    devices.append({"index": index, "name": torch.cuda.get_device_name(index),
                    "capability": list(torch.cuda.get_device_capability(index))})
assert devices, "No visible CUDA devices"
print(json.dumps({"status": "verified", "torch": torch.__version__,
                  "cuda": torch.version.cuda, "devices": devices}))
'''


def probe_cuda() -> subprocess.CompletedProcess:
    # Always a new interpreter: pip may have replaced a CPU-only wheel.
    return subprocess.run([sys.executable, "-B", "-c", PROBE], capture_output=True, text=True)


def provision_torch(run, *, required: bool = False) -> dict:
    """run(label, argv) must persist commands/output and raise on failure."""
    existing = probe_cuda()
    if existing.returncode == 0:
        report = json.loads(existing.stdout.strip().splitlines()[-1])
        report["action"] = "reused"
        print("[PASS] Existing Torch CUDA runtime and arithmetic verified", flush=True)
        return report
    gpus = detect_gpus()
    if not gpus:
        if required:
            raise RuntimeError("GPU test requires working NVIDIA CUDA; no nvidia-smi GPU detected")
        print("[INFO] No NVIDIA GPU detected through nvidia-smi; CUDA not provisioned. "
              "If this machine has NVIDIA hardware, install its driver and rerun.", flush=True)
        return {"status": "not_selected", "reason": "no NVIDIA GPU detected through nvidia-smi"}
    index = select_wheel(gpus)
    print(f"[RUN ] Provision Torch {TORCH_VERSION} ({index}) for detected NVIDIA GPU", flush=True)
    run("Install CUDA Torch", [sys.executable, "-m", "pip", "install", "--upgrade",
                              f"torch=={TORCH_VERSION}+{index}", "--index-url",
                              f"https://download.pytorch.org/whl/{index}"])
    run("Verify CUDA arithmetic", [sys.executable, "-B", "-c", PROBE])
    result = probe_cuda()
    if result.returncode:
        raise RuntimeError("CUDA verification failed after installation: " + result.stderr)
    report = json.loads(result.stdout.strip().splitlines()[-1])
    report.update(action="installed", wheel=index, detected_gpus=gpus)
    return report
