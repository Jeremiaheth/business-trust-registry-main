# Security

## Repo Hygiene

The public repo is protected by deterministic hygiene checks:

- `python -m btr_ng.cli lint-copy` blocks unsafe public claims and missing disclaimers.
- `python -m btr_ng.cli scan-repo-safety` blocks obvious personal-data patterns and forbidden public file types.
- Issue forms and PR templates reinforce the no-personal-data and links-only posture before content lands.

## CI Gates

`.github/workflows/ci.yml` runs the minimum release gates on pushes to `main` and on pull requests:

- Ruff
- mypy
- pytest
- `validate-ops`
- `validate-registry`
- `lint-copy`
- `scan-repo-safety`

These checks should stay required in branch protection.

## Release Verification

- `python -m btr_ng.cli build-api` writes `public/api/v1/manifests/latest.json`.
- `python -m btr_ng.cli verify-manifest --manifest public/api/v1/manifests/latest.json` recomputes sha256 and byte counts for each published API artifact.
- `score_and_build.yml` runs that verification step before the Pages artifact is uploaded.

This gives maintainers a repeatable way to prove that the published API output matches what the build produced.

## Workflow Permissions

- Current GitHub Actions use read-only `contents` permissions.
- The build workflow uploads artifacts but does not need repository write access.
- Any future workflow that requests broader scopes should justify them in code review.

## Cloudflare Credentials

- Cloudflare automation should use a scoped `CLOUDFLARE_API_TOKEN`.
- Global API keys should not be used in repo automation or stored in tracked files.
- Local scratch credential files such as `Cloudflare-API.txt` should remain ignored and should be treated as compromised once exposed.
- Cloudflare GitHub Actions should read only the token secret plus non-sensitive account, zone, project, and hostname variables.

## Branch Protection Expectations

`main` should be protected with:

- required CI status checks
- at least one human review before merge
- no force-pushes
- no bypass for routine content updates

The repo should remain safe even when a single maintainer is active, but branch protection reduces the chance of unsafe public data or unverifiable releases landing unnoticed.
