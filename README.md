# Rune Decrypter Prime

Rune Decrypter Prime (RDP) is a deterministic cryptanalysis toolkit for a
29-rune alphabet. It was built around Liber Primus work, but its ciphers,
scorers and solvers are useful beyond one text.

A high score is interesting. A run that can be repeated, inspected and proved
against the evidence is useful. RDP therefore keeps configuration, seeds, stop
reasons, truth use and reports visible. It rejects incompatible inputs instead
of quietly inventing a fallback.

RDP is an independent project by `mortlach`.

## Who this is for

The ordinary route is for technically capable people who are comfortable
reading Python and thinking critically about search results: cipher
researchers, puzzle solvers, engineers and curious Liber Primus readers. It
assumes no prior RDP knowledge. It also does not stop every few lines to explain
Python.

The public V1 surface is intentionally narrow:

```python
from rdp import api
```

Start there. Repository helpers and development campaigns exist, but they are
not a better version of the public API.

## Smallest installed-package check

This code works with an installed RDP package and uses no repository helper:

```python
from rdp import api

plaintext = (0, 3, 20, 20, 3, 7, 2, 18)
cipher = api.CipherSpec.vigenere()
key: api.ConcreteKey = (3, 1, 4)

ciphertext = api.encrypt(plaintext, cipher=cipher, key=key)
assert api.decrypt(ciphertext, cipher=cipher, key=key) == plaintext
```

Known-key operations use rune indices. The getting-started route makes the
Latin, rune and index views explicit before moving on to solver searches.

## Start from a source checkout

RDP requires Python 3.11 or newer. From the repository root:

```text
python install.py
python tutorials/v1/getting_started/01_known_key.py
```

On Windows, `install.bat` is an equivalent installer entry point.

Then follow the ten short files in
[`tutorials/v1/getting_started/`](tutorials/v1/getting_started/) or run the
default release selection:

```text
python tutorials/v1/run_tutorials.py
```

The default selection runs the complete starting route and three different,
bounded examples. Long P7/C7 qualifications are never hidden inside it.

## Read next

1. [`docs/setup/installation.md`](docs/setup/installation.md) — installation,
   assets and qualified platforms.
2. [`docs/guides/quickstart.md`](docs/guides/quickstart.md) — the ten-stop
   route and what each stop establishes.
3. [`docs/guides/anatomy_of_a_run.md`](docs/guides/anatomy_of_a_run.md) — how
   evidence, cipher, key space, solver, scoring and results fit together.
4. [`docs/guides/runes_and_text.md`](docs/guides/runes_and_text.md) — rune
   indices, word boundaries and text direction.
5. [`tutorials/v1/README.md`](tutorials/v1/README.md) — the complete runnable
   example catalogue, including assets, runtime and truth use.
6. [`docs/README.md`](docs/README.md) — guides, reference and expert paths.

## Repository map

```text
src/rdp/                         installed package source
tutorials/v1/getting_started/   ordered public-API route
tutorials/v1/examples/          runnable source-checkout examples
cipher_development/             bounded development and qualification tools
docs/                            user, expert and release-contract documents
tests/                           pytest suite
assets/                          source-bundled asset baseline
output/                          generated local evidence and logs
```

Generated `output/` is local evidence, not source.

## Release posture

V1 is qualified on Python 3.11 on Windows and Ubuntu. Push checks use the
bundled CI-light asset profile; the manual full proof verifies the complete V1
asset set, including the required V1 LM3/LM4 assets. Several-hour qualification
campaigns remain explicit, manual work under the repository's workflow-cost
policy.

The release contracts live under
[`docs/release_contracts/v1/`](docs/release_contracts/v1/). They are test-backed
drift controls, not the first reader path.

### Output and GPU setup

The source installer automatically provisions and verifies Torch CUDA on supported
NVIDIA machines. See [CUDA installation](docs/development/cuda_installation.md).
Generated output uses ignored source `output/` by default; developers can choose
an external project root with `RDP_OUTPUT_ROOT`. See
[output locations](docs/development/output_locations.md).
