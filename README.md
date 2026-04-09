# BTR-NG

BTR-NG is a public evidence dossier and verification layer for a narrow public beta. The repo publishes scored business profiles, procurement-derived signals, queue status, and a static public site based on available verified evidence.

## Operator Docs

- [Architecture](docs/architecture.md)
- [Cloudflare Deployment](docs/cloudflare.md)
- [Privacy](docs/privacy.md)
- [Security](docs/security.md)
- [Access Matrix](docs/access-matrix.md)
- [Moderation](docs/moderation.md)
- [Disputes](docs/disputes.md)
- [Seed Data](docs/seed-data.md)
- [Public Language Charter](docs/public-language-charter.md)

## Requirements

- Python 3.12 or 3.13
- Git

## Local Setup

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

If Python 3.12 is installed on your machine, replace `py -3.13` with `py -3.12`.

## Build Flow

The public beta build is deterministic and file-based:

```powershell
python -m btr_ng.cli validate-ops
python -m btr_ng.cli validate-seed-sources --source-dir data_sources/public_seed_sources
python -m btr_ng.cli validate-registry
python -m btr_ng.cli generate-real-seed --source-dir data_sources/public_seed_sources --registry-dir registry --nocopo-fixture-out tests/fixtures/nocopo/sample.json
python -m btr_ng.cli score --registry registry --out build/scores --ops-dir ops --ingestion-status healthy
python -m btr_ng.cli ingest-nocopo --input tests/fixtures/nocopo/sample.json --registry registry --out derived/nocopo
python -m btr_ng.cli report-ingestion-quality --input tests/fixtures/nocopo/sample.json --derived derived/nocopo --out derived/reports --ingestion-status healthy --max-age-days 30
python -m btr_ng.cli build-api --registry registry --scores build/scores --derived derived --out public/api/v1 --ops-dir ops --ingestion-status healthy
python -m btr_ng.cli verify-manifest --manifest public/api/v1/manifests/latest.json
python -m btr_ng.cli build-site --api public/api/v1 --templates site/templates --static-dir site/static --out site/dist
```

Published API artifacts are written under `public/api/v1/`, including per-business JSON, `search.json`, `queue_status.json`, and `manifests/latest.json`. The static site is rendered to `site/dist/`.

The committed seed set is generated from curated public-source snapshots under `data_sources/public_seed_sources/`. Regenerate the checked-in registry and OCDS fixture with `python -m btr_ng.cli generate-real-seed`.

## Cloudflare Deploy

Cloudflare deployment keeps the public site and API on one origin. Package the built Pages artifact with:

```powershell
python -m btr_ng.cli package-cloudflare-pages --site-dir site/dist --api-dir public/api/v1 --out build/cloudflare/pages
```

The public deploy target is Cloudflare Pages at `www.btr.dpdns.org`. The private lane remains a separate Cloudflare Python Worker preview until later cutover. See [Cloudflare Deployment](docs/cloudflare.md) for the required GitHub secret/vars and one-time dashboard setup.

## Quality Gates

```powershell
pytest -q
ruff check .
mypy src
python -m btr_ng.cli lint-copy
python -m btr_ng.cli scan-repo-safety
python -m btr_ng.cli safety-report
```

`python -m btr_ng.cli safety-report` exposes maintenance mode, active disputes, and queue state. `python -m btr_ng.cli show-scoring-config` prints the scoring weights and priors that drive the scorer.

## Make Targets

```text
make install
make test
make lint
make typecheck
make validate-ops
make validate-seed-sources
make validate-registry
make generate-real-seed
make show-scoring-config
make score
make ingest-nocopo
make report-ingestion-quality
make safety-report
make build-api
make build-site
make package-cloudflare-pages
make verify-manifest
make lint-copy
make scan-repo-safety
make check
```

## GitHub Actions

- `ci.yml` runs Ruff, mypy, pytest, `validate-ops`, `validate-seed-sources`, `validate-registry`, a seed-regeneration drift check, `lint-copy`, and `scan-repo-safety`.
- `score_and_build.yml` validates and regenerates committed seed data, rebuilds procurement-derived data, computes scores, builds the API, verifies the release manifest, builds the site, and uploads the Pages artifact.
- `ingest_nocopo.yml` validates and regenerates committed seed data, runs the deterministic NOCOPO fixture ingestion path, and uploads the derived outputs for inspection.
- `baseline_release.yml` rebuilds the public artifacts for `*-baseline` tags and publishes the API archive, site archive, release manifest, and seed provenance summary as a GitHub Release.
- `cloudflare_pages_deploy.yml` rebuilds the public artifacts, packages them for Cloudflare Pages, and deploys preview or production builds with Wrangler.
- `cloudflare_private_lane_deploy.yml` deploys the Cloudflare Python Worker preview for the private lane separately from the public Pages lane.

## Public Beta Boundaries

- This repo does not accept personal data, attachments, or raw evidence uploads.
- Public disputes are fact-correction workflows only.
- Procurement signals are derived from published procurement data and are complementary evidence.
- Scores are decision support only, and confidence indicates evidence completeness.
