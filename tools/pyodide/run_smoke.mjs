// Host only: load the pinned runtime, install the wheel, execute ordinary Python.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, realpath, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const toolDir = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(toolDir, '../..');
const pins = JSON.parse(await readFile(path.join(toolDir, 'versions.json'), 'utf8'));
const output = path.resolve(repo, process.env.RDP_PYODIDE_OUTPUT || 'build/pyodide');
const relativeOutput = path.relative(repo, output);
assert.ok(relativeOutput && (relativeOutput.startsWith('..' + path.sep) || path.isAbsolute(relativeOutput)
  || ['build', 'dist'].some(dir => relativeOutput === path.join(dir, 'pyodide')
    || relativeOutput.startsWith(path.join(dir, 'pyodide') + path.sep))),
  'Output must be external, or under build/pyodide or dist/pyodide');
const report = { status: 'FAIL', pins };
let py;
const started = performance.now();
try {
  assert.equal(process.argv.length, 2, 'Use environment settings, not arguments');
  assert.equal(process.versions.node, pins.node, `expected Node ${pins.node}`);
  assert.ok(process.env.RDP_PYODIDE_DIST, 'Set RDP_PYODIDE_DIST to the external pinned runtime directory');
  const runtime = await realpath(process.env.RDP_PYODIDE_DIST);
  const lock = JSON.parse(await readFile(path.join(runtime, 'pyodide-lock.json'), 'utf8'));
  assert.equal(lock.info.abi_version, pins.abi);
  assert.equal(lock.info.python, pins.python);
  assert.equal(lock.info.platform, `emscripten_${pins.emscripten.replaceAll('.', '_')}`);
  assert.equal(lock.info.arch, 'wasm32');
  for (const [name, version] of Object.entries(pins.runtime_packages)) {
    assert.equal(lock.packages[name].version, version, `expected ${name} ${version}`);
  }
  let wheelPath = process.env.RDP_PYODIDE_WHEEL;
  let receipt;
  if (!wheelPath) {
    receipt = JSON.parse(await readFile(path.join(output, 'wheel.json'), 'utf8'));
    assert.equal(receipt.status, 'PASS');
    wheelPath = path.resolve(output, receipt.wheel);
  }
  wheelPath = await realpath(path.resolve(repo, wheelPath));
  assert.ok(wheelPath.endsWith(`-${pins.wheel_tag}.whl`), `expected wheel tag ${pins.wheel_tag}`);
  const bytes = await readFile(wheelPath);
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  if (receipt) assert.equal(sha256, receipt.sha256, 'Wheel differs from build receipt');
  report.wheel = { filename: path.basename(wheelPath), sha256, size_bytes: bytes.length };
  await mkdir(output, { recursive: true });
  const cache = path.join(output, 'package-cache');
  await mkdir(cache, { recursive: true });
  const runtimeModule = await import(pathToFileURL(path.join(runtime, 'pyodide.mjs')).href);
  assert.equal(runtimeModule.version, pins.pyodide, `expected Pyodide ${pins.pyodide}`);
  // No NODEFS mounts and no inherited environment: the checkout cannot mask
  // missing wheel contents. Only wheel bytes and smoke.py enter this filesystem.
  py = await runtimeModule.loadPyodide({
    indexURL: runtime + path.sep,
    packageCacheDir: cache,
    env: { PYTHONUTF8: '1', PYTHONDONTWRITEBYTECODE: '1', RDP_OUTPUT_ROOT: '/tmp/rdp-smoke' },
    stdout: line => console.log(line), stderr: line => console.error(line),
  });
  assert.equal(py.version, pins.pyodide);
  assert.equal(py.runPython('import platform; platform.python_version()'), pins.python);
  await py.loadPackage(Object.keys(pins.runtime_packages));
  const virtualWheel = '/tmp/' + path.basename(wheelPath);
  py.FS.writeFile(virtualWheel, bytes);
  py.globals.set('rdp_wheel_path', virtualWheel);
  py.globals.set('rdp_dependency_pins', JSON.stringify(pins.python_packages));
  await py.runPythonAsync(`
import importlib.metadata, json, os, micropip
await micropip.install([f'{name}=={version}' for name, version in json.loads(rdp_dependency_pins).items()])
await micropip.install('emfs:' + rdp_wheel_path)
os.environ['RDP_SMOKE_WHEEL'] = rdp_wheel_path
`);
  py.globals.set('rdp_all_dependency_pins', JSON.stringify({ ...pins.runtime_packages, ...pins.python_packages }));
  py.runPython(`
for name, expected in json.loads(rdp_all_dependency_pins).items():
    actual = importlib.metadata.version(name)
    assert actual == expected, f'expected {name} {expected} but found {actual}'
`);
  py.globals.set('__name__', '__main__');
  await py.runPythonAsync(await readFile(path.join(toolDir, 'smoke.py'), 'utf8'));
  assert.equal(py.globals.get('SMOKE_RESULT').get('status'), 'PASS');
  report.status = 'PASS';
} catch (error) {
  report.error = String(error.stack || error);
  console.error(report.error);
  process.exitCode = 1;
} finally {
  if (py && py.globals.has('SMOKE_JSON')) report.smoke = JSON.parse(py.globals.get('SMOKE_JSON'));
  report.seconds = (performance.now() - started) / 1000;
  await mkdir(output, { recursive: true });
  await writeFile(path.join(output, 'smoke.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(`WASM smoke ${report.status} (${report.seconds.toFixed(2)}s)`);
}
