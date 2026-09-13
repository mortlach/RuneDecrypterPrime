#!/usr/bin/env bash
# Requires an activated, externally installed toolchain. No bootstrap or upgrades.
set -euo pipefail
[[ $# == 0 ]] || { echo 'Use the environment settings in tools/pyodide/README.md, not arguments.' >&2; exit 2; }
tool_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export RDP_BUILD_REPO="$(cd -- "$tool_dir/../.." && pwd)"
export RDP_BUILD_PINS="$tool_dir/versions.json"
: "${PYODIDE_XBUILDENV_PATH:?Set PYODIDE_XBUILDENV_PATH to the existing external xbuildenv}"
[[ -d "$PYODIDE_XBUILDENV_PATH" ]] || { echo 'External xbuildenv directory does not exist' >&2; exit 1; }
for tool in python pyodide emcc node git tar mktemp; do
    command -v "$tool" >/dev/null || { echo "Required tool not found: $tool" >&2; exit 1; }
done
export PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 PYTHONUNBUFFERED=1
export RDP_PYODIDE_OUTPUT="${RDP_PYODIDE_OUTPUT:-$RDP_BUILD_REPO/build/pyodide}"
export RDP_BUILD_STARTED="$(python -c 'import time; print(time.time())')"

# Pin the selected environment, not merely a compiler found somewhere on PATH.
python - <<'PY'
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys

repo = Path(os.environ['RDP_BUILD_REPO'])
pins = json.loads(Path(os.environ['RDP_BUILD_PINS']).read_text())
if Path(os.environ['PYODIDE_XBUILDENV_PATH']).resolve().is_relative_to(repo):
    raise SystemExit('PYODIDE_XBUILDENV_PATH must be outside the source checkout')
def command(*args):
    return subprocess.check_output(args, text=True).strip()
def require(name, actual, expected):
    if actual != expected:
        raise SystemExit(f'expected {name} {expected} but found {actual}')
    print(f'{name}: {actual}')
require('Python', '.'.join(map(str, sys.version_info[:3])), pins['python'])
require('pyodide-build', metadata.version('pyodide-build'), pins['pyodide_build'])
require('pyodide-cli', metadata.version('pyodide-cli'), pins['pyodide_cli'])
cli = command('pyodide', '--version')
if f"pyodide-build version: {pins['pyodide_build']}" not in cli:
    raise SystemExit('python and pyodide must belong to the same pinned environment')
for key, pin in (('python_version', 'python'), ('emscripten_version', 'emscripten'),
                 ('pyodide_abi_version', 'abi')):
    require(key, command('pyodide', 'config', 'get', key), pins[pin])
require('Pyodide xbuildenv', command('pyodide', 'xbuildenv', 'version'), pins['pyodide'])
banner = command('emcc', '--version')
match = re.search(r'^emcc \(Emscripten[^\n]*\) (\d+\.\d+\.\d+)(?:\s|$)', banner, re.M)
require('emcc', match.group(1) if match else banner, pins['emscripten'])
require('Node', command('node', '--version').removeprefix('v'), pins['node'])
# Do not inherit local compiler/backend overrides into a release build.
for name in ('CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'EMCC_CFLAGS', 'CC', 'CXX',
             'PYTHONPATH', 'PYTHONOPTIMIZE'):
    if os.environ.get(name):
        raise SystemExit(f'unset {name} before building with the pinned defaults')
output = Path(os.environ['RDP_PYODIDE_OUTPUT'])
output = (repo / output).resolve()
if output == repo or (output.is_relative_to(repo) and not any(
        output.is_relative_to(repo / name / 'pyodide') for name in ('build', 'dist'))):
    raise SystemExit('output must be external, or under build/pyodide or dist/pyodide')
if (output / 'wheel.json').exists():
    raise SystemExit('output already contains a build receipt; choose a fresh RDP_PYODIDE_OUTPUT')
output.mkdir(parents=True, exist_ok=True)
print('Source revision:', command('git', '-C', str(repo), 'rev-parse', 'HEAD'))
print('Output:', output)
PY

# Resolve relative output paths against the script's repository, never caller cwd.
if [[ "$RDP_PYODIDE_OUTPUT" != /* ]]; then
    RDP_PYODIDE_OUTPUT="$RDP_BUILD_REPO/$RDP_PYODIDE_OUTPUT"
fi
RDP_PYODIDE_OUTPUT="$(cd -- "$RDP_PYODIDE_OUTPUT" && pwd)"
export RDP_PYODIDE_OUTPUT
export RDP_BUILD_STAGE="$(mktemp -d "$RDP_PYODIDE_OUTPUT/source.XXXXXXXX")"
mkdir -p -- "$RDP_PYODIDE_OUTPUT/wheels" "$RDP_PYODIDE_OUTPUT/tmp"
export TMPDIR="$RDP_PYODIDE_OUTPUT/tmp"
# Current tracked file contents, including reviewed working changes. Untracked
# Full-V1 downloads, caches and build outputs never enter the staging tree.
git -C "$RDP_BUILD_REPO" ls-files -z |
    tar -C "$RDP_BUILD_REPO" --null --verbatim-files-from -T - -cf - |
    tar -C "$RDP_BUILD_STAGE" -xf -
(
    cd -- "$RDP_BUILD_STAGE"
    pyodide build . --outdir "$RDP_PYODIDE_OUTPUT/wheels"
)

# Verify the produced release artifact before advertising it to the smoke host.
python - <<'PY'
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from zipfile import ZipFile

repo = Path(os.environ['RDP_BUILD_REPO'])
output = Path(os.environ['RDP_PYODIDE_OUTPUT'])
pins = json.loads(Path(os.environ['RDP_BUILD_PINS']).read_text())
wheels = list((output / 'wheels').glob('*.whl'))
assert len(wheels) == 1, f'expected one newly built wheel, found {wheels}'
wheel = wheels[0]
assert wheel.name.endswith('-' + pins['wheel_tag'] + '.whl'), wheel.name
with ZipFile(wheel) as archive:
    names = archive.namelist()
    metadata = archive.read(next(n for n in names if n.endswith('.dist-info/WHEEL'))).decode()
    assert 'Tag: ' + pins['wheel_tag'] in metadata
    manifest_path = 'rdp/data/assets_manifest_ci_light_v1.json'
    manifest = json.loads(archive.read(manifest_path))
    source_manifest = Path(os.environ['RDP_BUILD_STAGE']) / 'assets/manifests/assets_manifest_ci_light_v1.json'
    assert manifest == json.loads(source_manifest.read_text())
    prefix = 'rdp/data/assets/'
    expected = {prefix + row['final_relpath'] for row in manifest['installed_assets']}
    expected.add(prefix + 'language_model/lmp/index.json')
    assert {n for n in names if n.startswith(prefix) and not n.endswith('/')} == expected
    for row in manifest['installed_assets']:
        data = archive.read(prefix + row['final_relpath'])
        assert len(data) == row['size_bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    extensions = [n for n in names if n.endswith('.so')]
    assert len(extensions) == 3 and all(archive.read(n).startswith(b'\0asm') for n in extensions)
    for stem in ('language_model/_fastlm.', 'hamming/_hamming.', 'span_hamming/_span_hamming_fast.'):
        assert any(n.startswith('rdp/scoring/' + stem) for n in extensions), stem
    assert 'rdp/data/liber_primus/solved_plaintext/welcome_pilgrim.txt' in names
    assert all(n.startswith(('rdp/',)) or '.dist-info/' in n for n in names)
    assert not any(n.endswith(('.cpp', '.hpp', '.h', '.pyc', '.log')) for n in names)
receipt = {
    'status': 'PASS', 'wheel': wheel.relative_to(output).as_posix(),
    'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(), 'size_bytes': wheel.stat().st_size,
    'tag': pins['wheel_tag'], 'pins': pins,
    'source_revision': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
    'source_status': subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True),
    'build_seconds': time.time() - float(os.environ['RDP_BUILD_STARTED']),
}
(output / 'wheel.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt, indent=2))
PY
