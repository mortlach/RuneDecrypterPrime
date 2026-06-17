# Troubleshooting

Status: user guide

Start here when install or tutorials fail.

## Check your working directory

Run commands from the repository root.

You should see files such as:

```text
README.md
install.py
pyproject.toml
tutorials/
docs/
```

## Check Python

RDP V1 expects Python 3.11+.

## Re-run install

```text
python install.py
```

On Windows:

```text
install.bat
```

## Re-run tutorials

```text
python tutorials/v1/run_all.py
```

Success means:

```text
failed   : 0
```

## Common causes

```text
wrong Python environment
package not installed
optional asset missing
wrong tutorial gate profile
stale generated output
running from the wrong folder
```

## Output to inspect

```text
output/install_logs/
output/tutorials/
```

## When asking for help

Include:

```text
Python version
operating system
command you ran
tutorial gate profile
asset profile
first failing tutorial name
relevant output path
```
