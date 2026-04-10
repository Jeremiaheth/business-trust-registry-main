# Architecture

## Purpose

BTR-NG is a file-first public beta. It produces a public read plane from validated registry records, deterministic scoring logic, a React trust portal that consumes generated API artifacts, and a separate public intake Worker for moderated web submissions.

## Core Components

### Registry

- `registry/businesses/` contains the public business profiles.
- `registry/evidence/` contains public evidence references and metadata.
- `registry/disputes/` contains fact-correction cases that can force under-review behavior.
- `python -m btr_ng.cli validate-registry` enforces the schema contract before anything is scored or published.

### Scorer

- `spec/scoring.toml` defines weights, priors, thresholds, and identity rules.
- `src/btr_ng/scoring/engine.py` converts registry evidence into deterministic score snapshots.
- Score output is written to `build/scores/` as per-business JSON.
- Confidence indicates evidence completeness, not legal certainty.

### Safety Controller

- `src/btr_ng/safety/controller.py` evaluates disputes, procurement freshness, queue pressure, and operator policy.
- Safety decisions can suppress normal scoring or move the system into maintenance mode.
- `src/btr_ng/safety/queue_status.py` emits queue state for the public read plane.

### Ingestion

- `src/btr_ng/ingestion/nocopo.py` ingests local NOCOPO or OCDS fixtures into `derived/nocopo/`.
- `src/btr_ng/ingestion/quality.py` writes freshness and anomaly summaries to `derived/reports/`.
- Procurement evidence is derived from published procurement data and must remain visibly stale when freshness drops.

### API Builder

- `src/btr_ng/publishing/api_builder.py` combines registry records, score snapshots, procurement-derived outputs, and queue status.
- It publishes `public/api/v1/index.json`, `search.json`, `queue_status.json`, per-business JSON, per-business report JSON, and `manifests/latest.json`.
- `src/btr_ng/release/manifest.py` computes the checksum manifest for the published API artifacts.

### Trust Portal Frontend

- `frontend/` contains the Vite + React trust portal.
- The frontend reads the generated public API from the same origin under `/api/v1/`.
- Pages are route-driven: homepage, directory, business profile, report, about, and contact.
- CAC, PSC, sector, and location gaps are rendered explicitly as unavailable-beta states rather than inferred data.

### Public Intake Worker

- `public_intake/` contains a separate Cloudflare Worker for `GET /health` and `POST /api/intake/{contact,claim,correction}`.
- The Worker stores intake records in D1 and verifies Turnstile tokens before persisting requests.
- Public web intake is operationally separate from the private-lane Python Worker.

## Build Sequence

1. Validate ops and registry contracts.
2. Ingest procurement fixture data and write freshness reports.
3. Build a runtime safety report.
4. Compute per-business trust scores.
5. Build the public API and release manifest.
6. Verify the manifest.
7. Build the React trust portal from the API output.
8. Package the SPA root and `/api/v1/` for Pages deployment.

## Operational Notes

- The repo is the source of truth for the public beta inputs.
- The public API and site are derived artifacts and can be rebuilt locally or in GitHub Actions.
- Cloudflare Pages packages the React site root and the generated `api/v1/` artifacts into one deploy directory so the public product stays same-origin.
- Public website submissions are not written to the repo. They flow through the public intake Worker into D1.
- The private lane is a separate Cloudflare Python Worker deployment and should remain operationally independent from the public Pages lane.
- Another maintainer should be able to reason about the public surface from the registry, derived artifacts, and docs in this folder without a live backend dependency.
