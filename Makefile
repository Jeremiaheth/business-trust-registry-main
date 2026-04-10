PYTHON ?= python
NODE20_RUN ?= npx -p node@20 node

.PHONY: install frontend-install frontend-test frontend-build public-intake-install public-intake-test public-intake-typecheck test lint typecheck validate-ops validate-registry validate-seed-sources generate-real-seed show-scoring-config score ingest-nocopo report-ingestion-quality safety-report build-api build-site package-cloudflare-pages verify-manifest lint-copy scan-repo-safety check

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]

frontend-install:
	cd frontend && npm install

frontend-test:
	cd frontend && $(NODE20_RUN) node_modules/vitest/vitest.mjs run

frontend-build:
	cd frontend && $(NODE20_RUN) node_modules/vite/bin/vite.js build

public-intake-install:
	cd public_intake && npm install

public-intake-test:
	cd public_intake && $(NODE20_RUN) node_modules/vitest/vitest.mjs run

public-intake-typecheck:
	cd public_intake && $(NODE20_RUN) node_modules/typescript/bin/tsc --noEmit

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
	$(MAKE) frontend-build

package-cloudflare-pages:
	$(PYTHON) -m btr_ng.cli package-cloudflare-pages --site-dir site/dist --api-dir public/api/v1 --out build/cloudflare/pages

verify-manifest:
	$(PYTHON) -m btr_ng.cli verify-manifest --manifest public/api/v1/manifests/latest.json

lint-copy:
	$(PYTHON) -m btr_ng.cli lint-copy

scan-repo-safety:
	$(PYTHON) -m btr_ng.cli scan-repo-safety

check: test lint typecheck validate-ops validate-seed-sources validate-registry frontend-test public-intake-test public-intake-typecheck lint-copy scan-repo-safety
