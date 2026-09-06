# Requirements files

The files under `requirements/targets/` are retained dependency fragments for
specialised repository tooling. They are not install targets exposed by
`install.py`.

For a normal source installation, use:

```text
python install.py
```

For the bounded CI-light setup, the owning entry point is:

```text
python tools/ci/install_light.py
```

Do not infer a supported installer command from filenames such as `runner.txt`
or `organiser.txt`. A repository tool that still consumes one of these files
should document that dependency at the tool itself.

See [installation](../docs/setup/installation.md) for the supported user route.
