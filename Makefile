PYTHON ?= python

.PHONY: install test lint typecheck validate-ops validate-registry show-scoring-config score safety-report build-api build-site lint-copy check

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

safety-report:
	$(PYTHON) -m btr_ng.cli safety-report

build-api:
	$(PYTHON) -m btr_ng.cli build-api --registry registry --scores build/scores --derived derived --out public/api/v1

build-site:
	$(PYTHON) -m btr_ng.cli build-site --api public/api/v1 --templates site/templates --static-dir site/static --out site/dist

lint-copy:
	$(PYTHON) -m btr_ng.cli lint-copy

check: test lint typecheck validate-ops validate-registry lint-copy
