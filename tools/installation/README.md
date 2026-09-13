# Platform installer wrappers

The standard source-install entry point remains at the repository root:

```text
python install.py
```

These optional platform wrappers invoke that same root installer:

```text
tools/installation/install.ps1
tools/installation/install.bat
tools/installation/install.sh
```

Run a wrapper from any working directory. Each wrapper resolves the repository
root from its own location and forwards any supplied installer arguments.
