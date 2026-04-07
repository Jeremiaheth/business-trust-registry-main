PYTHON ?= python

.PHONY: install test lint typecheck validate-ops validate-registry show-scoring-config score ingest-nocopo report-ingestion-quality safety-report build-api build-site lint-copy scan-repo-safety check

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

lint-copy:
	$(PYTHON) -m btr_ng.cli lint-copy

scan-repo-safety:
	$(PYTHON) -m btr_ng.cli scan-repo-safety

check: test lint typecheck validate-ops validate-registry lint-copy scan-repo-safety
