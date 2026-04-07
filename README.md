# BTR-NG

BTR-NG is a Python-first public evidence dossier and verification layer. This repository starts with the public beta bootstrap defined in the project runbook.

## Requirements

- Python 3.12 or 3.13
- Git

## Setup

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

If Python 3.12 is installed on your machine, replace `py -3.13` with `py -3.12`.

## Developer Commands

```powershell
pytest -q
ruff check .
mypy src
python -m btr_ng.cli --help
python -m btr_ng.cli version
python -m btr_ng.cli validate-ops
```

## Make Targets

```text
make install
make test
make lint
make typecheck
make validate-ops
make check
```

## Scope

This bootstrap covers Step 01 of the runbook:

- Python packaging with a `src` layout
- Minimal CLI entrypoint
- Test, lint, and type-check configuration
- CI baseline
- Contributor and security policy files

The repository also includes Step 02 governance defaults under [`ops/`](ops/), with a `validate-ops` CLI command that enforces solo-safe configuration rules.
