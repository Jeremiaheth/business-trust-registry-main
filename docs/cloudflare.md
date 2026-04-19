# Cloudflare Deployment

## Purpose

BTR-NG uses Cloudflare in two separate lanes:

- the public read plane is deployed as a single-origin Cloudflare Pages site at `www.btr.dpdns.org`
- the public intake lane is a separate Cloudflare Worker at `forms.btr.dpdns.org`
- the private lane remains a separate Cloudflare Python Worker preview on `workers.dev` until a later cutover to `intake.btr.dpdns.org`

The public Pages deployment serves both the React trust portal and the static JSON API from one origin. The packaged deploy directory places the site at the root and the API under `/api/v1/`.

## Authentication

Use a scoped Cloudflare API token for automation. Do not use a global API key in local scripts, GitHub Actions, or checked-in files.

Local auth options:

- `npx wrangler login` for interactive local Pages work
- `CLOUDFLARE_API_TOKEN` for headless local deploys and GitHub Actions

The local scratch file `Cloudflare-API.txt` should be treated as compromised credential material. Rotate the old key, keep the file out of version control, and do not use it for automation.

## Required GitHub Configuration

GitHub Actions expects:

- secret: `CLOUDFLARE_API_TOKEN`
- secret: `CLOUDFLARE_PAGES_API_TOKEN`
- secret: `CLOUDFLARE_TURNSTILE_SECRET_KEY`
- vars:
  - `CLOUDFLARE_ACCOUNT_ID=92353cdf85a371b9985b7a46cf677ccd`
  - `CLOUDFLARE_ZONE_ID=16200b24cac290f487c7214793939a12`
  - `CLOUDFLARE_PAGES_PROJECT=btr-ng-public`
  - `CLOUDFLARE_PUBLIC_HOST=www.btr.dpdns.org`
  - `CLOUDFLARE_APEX_HOST=btr.dpdns.org`
  - `CLOUDFLARE_PUBLIC_INTAKE_WORKER_NAME=btr-ng-public-intake`
  - `CLOUDFLARE_PUBLIC_INTAKE_HOST=forms.btr.dpdns.org`
  - `CLOUDFLARE_PUBLIC_INTAKE_D1_NAME=btr-ng-public-intake`
  - `CLOUDFLARE_PUBLIC_INTAKE_D1_DATABASE_ID=<cloudflare d1 id>`
  - `CLOUDFLARE_PUBLIC_INTAKE_D1_PREVIEW_DATABASE_ID=<cloudflare preview d1 id>`
  - `CLOUDFLARE_TURNSTILE_SITE_KEY=<turnstile site key>`
  - `CLOUDFLARE_PRIVATE_WORKER_NAME=btr-ng-private-lane`
  - `CLOUDFLARE_PRIVATE_HOST=intake.btr.dpdns.org`

## Public Pages Setup

One-time operator setup:

1. Create the Pages project `btr-ng-public` in Cloudflare under account `92353cdf85a371b9985b7a46cf677ccd`.
2. Add `www.btr.dpdns.org` as the production custom domain for that Pages project.
3. Add a zone-level redirect from `https://btr.dpdns.org/*` to `https://www.btr.dpdns.org/:splat` with a permanent redirect.
4. Add the scoped `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_PAGES_API_TOKEN` secrets in GitHub.

Repo commands used by the deploy workflow:

```powershell
python -m btr_ng.cli validate-ops
python -m btr_ng.cli validate-seed-sources --source-dir data_sources/public_seed_sources
python -m btr_ng.cli generate-real-seed --source-dir data_sources/public_seed_sources --registry-dir registry --nocopo-fixture-out tests/fixtures/nocopo/sample.json
python -m btr_ng.cli score --registry registry --out build/scores --ops-dir ops --ingestion-status healthy
python -m btr_ng.cli ingest-nocopo --input tests/fixtures/nocopo/sample.json --registry registry --out derived/nocopo
python -m btr_ng.cli report-ingestion-quality --input tests/fixtures/nocopo/sample.json --derived derived/nocopo --out derived/reports --ingestion-status healthy --max-age-days 30
python -m btr_ng.cli build-api --registry registry --scores build/scores --derived derived --out public/api/v1 --ops-dir ops --ingestion-status healthy
python -m btr_ng.cli verify-manifest --manifest public/api/v1/manifests/latest.json
npx -p node@20 node frontend/node_modules/vite/bin/vite.js build
python -m btr_ng.cli package-cloudflare-pages --site-dir site/dist --api-dir public/api/v1 --out build/cloudflare/pages
```

The workflow then uploads `build/cloudflare/pages` with the Pages upload-token flow so the site and API stay on the same origin without depending on Wrangler account-membership auth.

## Public Intake Worker

The public forms flow is a separate Worker with D1-backed moderation intake:

- `GET /health`
- `POST /api/intake/contact`
- `POST /api/intake/claim`
- `POST /api/intake/correction`

One-time operator setup:

1. Create the D1 database for `btr-ng-public-intake`.
2. Create a Turnstile widget and capture the site key and secret.
3. Add `forms.btr.dpdns.org` as the custom domain target for the Worker.
4. Set the GitHub secret/vars listed above.

The deploy workflow applies `public_intake/migrations/0001_public_intake.sql` through the D1 REST API and uploads the Worker through the Workers REST API. Public beta safeguards remain strict:

- Turnstile is required for submission endpoints.
- contact, claim, and correction forms accept public links and hashes only.
- attachments are rejected.
- submissions are written to D1, not to GitHub and not to the repo.

## Private-Lane Worker

Phase 1 preview:

- deploy `private_lane/` with `uv run pywrangler deploy`
- keep `workers_dev = true`
- keep the Worker on the generated `workers.dev` preview URL only
- keep the current minimal surface: `GET /health` and `POST /intake/validate`

Phase 2 cutover:

1. provision D1 and R2 only when queue/storage activation is intentional
2. apply `private_lane/migrations/0001_private_case_queue.sql`
3. bind the new resources in `private_lane/wrangler.toml`
4. attach `intake.btr.dpdns.org` as the Worker custom domain
5. keep uploads disabled by default unless policy gates change deliberately

## Workflows

- `cloudflare_pages_deploy.yml` handles preview and production Pages deploys from GitHub Actions
- `cloudflare_public_intake_deploy.yml` handles public intake Worker deploys, D1 migration application, and custom-domain deployment
- `cloudflare_private_lane_deploy.yml` handles the private-lane preview Worker deploy independently of the public Pages lane

These workflows are intentionally separate so the public site and the private lane can be promoted independently.
