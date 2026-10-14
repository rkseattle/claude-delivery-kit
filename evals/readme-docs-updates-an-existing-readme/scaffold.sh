#!/usr/bin/env bash
# A small Python CLI whose README is stale (old version, old Python floor), has a custom
# Benchmarks section the template has no slot for, has no Usage or License heading, and
# whose Benchmarks anchor is linked from CONTRIBUTING.md.
set -euo pipefail
mkdir -p src/notely docs
cat > pyproject.toml <<'TOML'
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "notely"
version = "2.1.0"
requires-python = ">=3.10"
license = {text = "MIT"}

[project.scripts]
notely = "notely.cli:main"
TOML
printf 'MIT License\n' > LICENSE
printf '' > src/notely/__init__.py
cat > src/notely/cli.py <<'PY'
import sys


def main():
    print("added:", " ".join(sys.argv[2:]))
PY
cat > CONTRIBUTING.md <<'MD'
# Contributing

Re-run the numbers in [Benchmarks](README.md#benchmarks) before changing the store.
MD
cat > README.md <<'MD'
# notely

Notes from the command line.

## Benchmarks

Adding 10,000 notes takes 1.8 s on an M2 laptop; listing them takes 0.2 s.

## Installing

Requires Python 3.7+.

```sh
pip install notely==1.4
```

## Running it

```sh
notely add "buy milk"
```
MD
