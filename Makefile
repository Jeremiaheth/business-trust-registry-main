PYTHON ?= python

.PHONY: install test lint typecheck validate-ops validate-registry validate-seed-sources generate-real-seed show-scoring-config score ingest-nocopo report-ingestion-quality safety-report build-api build-site verify-manifest lint-copy scan-repo-safety check

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy src

validate-ops:
	$(PYTHON) -m btr_ng.cli validate-ops

validate-registry:
	$(PYTHON) -m btr_ng.cli validate-registry

validate-seed-sources:
	$(PYTHON) -m btr_ng.cli validate-seed-sources --source-dir data_sources/public_seed_sources

generate-real-seed:
	$(PYTHON) -m btr_ng.cli generate-real-seed --source-dir data_sources/public_seed_sources --registry-dir registry --nocopo-fixture-out tests/fixtures/nocopo/sample.json

show-scoring-config:
	$(PYTHON) -m btr_ng.cli show-scoring-config

score:
	$(PYTHON) -m btr_ng.cli score --registry registry --out build/scores

ingest-nocopo:
	$(PYTHON) -m btr_ng.cli ingest-nocopo --input tests/fixtures/nocopo/sample.json --registry registry --out derived/nocopo

report-ingestion-quality:
	$(PYTHON) -m btr_ng.cli report-ingestion-quality --input tests/fixtures/nocopo/sample.json --derived derived/nocopo --out derived/reports --ingestion-status healthy --max-age-days 30

safety-report:
	$(PYTHON) -m btr_ng.cli safety-report

build-api:
	$(PYTHON) -m btr_ng.cli build-api --registry registry --scores build/scores --derived derived --out public/api/v1

build-site:
	$(PYTHON) -m btr_ng.cli build-site --api public/api/v1 --templates site/templates --static-dir site/static --out site/dist

verify-manifest:
	$(PYTHON) -m btr_ng.cli verify-manifest --manifest public/api/v1/manifests/latest.json

lint-copy:
	$(PYTHON) -m btr_ng.cli lint-copy

scan-repo-safety:
	$(PYTHON) -m btr_ng.cli scan-repo-safety

check: test lint typecheck validate-ops validate-seed-sources validate-registry lint-copy scan-repo-safety
