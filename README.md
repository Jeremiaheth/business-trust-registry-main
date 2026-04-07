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
python -m btr_ng.cli validate-registry
python -m btr_ng.cli show-scoring-config
python -m btr_ng.cli score --registry registry --out build/scores
python -m btr_ng.cli safety-report
python -m btr_ng.cli build-api --registry registry --scores build/scores --derived derived --out public/api/v1
```

## Make Targets

```text
make install
make test
make lint
make typecheck
make validate-ops
make validate-registry
make show-scoring-config
make score
make safety-report
make build-api
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

Canonical public JSON contracts now live under [`spec/schema/`](spec/schema/) and are compiled and tested from Python before later registry and publishing steps build on them.

Seed registry data now lives under [`registry/`](registry/), and `validate-registry` checks each JSON file against the canonical schema associated with its registry lane.

Scoring configuration now lives in [`spec/scoring.toml`](spec/scoring.toml), and `show-scoring-config` loads and validates that contract without computing final scores yet.

Deterministic score snapshots are written with `score --registry registry --out build/scores`, using only local registry data and the configured Bayesian priors, evidence weights, and time-decay rules.

Safety decisions are exposed with `safety-report`, and the scorer now consumes those decisions so active disputes and maintenance conditions can suppress normal scoring behavior deterministically.

Static API artifacts are now built with `build-api`, which turns validated registry records and trust score snapshots into `public/api/v1/index.json`, per-business detail documents, `search.json`, and a checksum manifest.
