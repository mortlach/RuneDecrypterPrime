# Requirements files

The files under `requirements/targets/` support specialised repository tools and
CI paths.

For a normal source install:

```text
python install.py
```

The lightweight CI installer has its own maintainer entry point:

```text
python tools/ci/install_light.py
```

A requirements filename is not a second user-facing installation mode unless
the tool using it says so.
