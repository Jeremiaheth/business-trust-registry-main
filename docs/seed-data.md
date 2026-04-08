# Seed Data

The checked-in registry seed set is a small curated sample generated from committed public-source snapshots. It is intentionally limited to three businesses so the public pipeline stays deterministic while still covering the main product states:

- one published profile with stronger procurement evidence
- one under-review profile with a repo-owned dispute
- one insufficient-evidence profile with older public procurement references

## Source Snapshots

- Federal NOCOPO/OCDS sample
  - Publication: `https://data.open-contracting.org/en/publication/64`
  - Download: `https://fastly.data.open-contracting.org/downloads/nigeria_portal/3433/2026.jsonl.gz`
  - Licence: `PDDL`
  - Retrieved: `2026-04-08T00:00:00Z`
  - Reason: provides current federal supplier references with repeated award observations
- Anambra State OCDS sample
  - Publication: `https://data.open-contracting.org/en/publication/127`
  - Download: `https://fastly.data.open-contracting.org/downloads/nigeria_anambra_state/3183/full.jsonl.gz`
  - Licence: `PDDL`
  - Retrieved: `2026-04-08T00:00:00Z`
  - Reason: provides older state procurement references to preserve the thin-evidence path under current time-decay rules

The committed snapshot files live in `data_sources/public_seed_sources/` and include only the curated releases used by the seed generator.

## Regeneration

Regenerate the checked-in registry and aligned OCDS fixture with:

```powershell
python -m btr_ng.cli generate-real-seed --source-dir data_sources/public_seed_sources --registry-dir registry --nocopo-fixture-out tests/fixtures/nocopo/sample.json
```

The generator rewrites:

- `registry/businesses/*.json`
- `registry/evidence/*.json`
- `registry/disputes/*.json`
- `tests/fixtures/nocopo/sample.json`

No network access is required during normal development or CI. The committed snapshots and `seed_manifest.json` are the source of truth.
