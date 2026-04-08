# Seed Data

The checked-in registry seed set is a curated deterministic pack generated from committed public-source snapshots. It currently contains 12 businesses so the public pipeline exercises broader search, scoring, dispute, and publishing behavior while still staying small enough for review and CI:

- 8 active profiles with current federal procurement references
- 2 under-review profiles with repo-owned disputes layered on top of current federal references
- 2 naturally insufficient-evidence profiles with older state procurement references

## Source Snapshots

- Federal NOCOPO/OCDS sample
  - Publication: `https://data.open-contracting.org/en/publication/64`
  - Download: `https://fastly.data.open-contracting.org/downloads/nigeria_portal/3433/2026.jsonl.gz`
  - Licence: `PDDL`
  - Retrieved: `2026-04-08T00:00:00Z`
  - Reason: provides current federal supplier references and the deterministic federal NOCOPO fixture used for derived procurement metrics
- Anambra State OCDS sample
  - Publication: `https://data.open-contracting.org/en/publication/127`
  - Download: `https://fastly.data.open-contracting.org/downloads/nigeria_anambra_state/3183/full.jsonl.gz`
  - Licence: `PDDL`
  - Retrieved: `2026-04-08T00:00:00Z`
  - Reason: provides older state procurement references that naturally fall below the confidence threshold under the current time-decay rules

The committed snapshot files live in `data_sources/public_seed_sources/` and include only projected release fields needed by the seed generator and fixture builder:

- source metadata: `source_id`, `publication_url`, `download_url`, `license`, `retrieved_at`
- release fields: `ocid`, date field, buyer name, selected awards and suppliers, and selected contract title/description fallback data

The seed pipeline rejects extra projected fields, email-like strings, and phone-like strings before it writes anything to `registry/`.

Every generated business must remain traceable to at least one committed `(source_id, ocid, award_id)` tuple declared in `seed_manifest.json`.

## Regeneration

Regenerate the checked-in registry and aligned OCDS fixture with:

```powershell
python -m btr_ng.cli validate-seed-sources --source-dir data_sources/public_seed_sources
python -m btr_ng.cli generate-real-seed --source-dir data_sources/public_seed_sources --registry-dir registry --nocopo-fixture-out tests/fixtures/nocopo/sample.json
```

The generator rewrites:

- `registry/businesses/*.json`
- `registry/evidence/*.json`
- `registry/disputes/*.json`
- `tests/fixtures/nocopo/sample.json`

No network access is required during normal development or CI. The committed snapshots and `seed_manifest.json` are the source of truth.

The generated federal fixture sets `publishedDate` from the committed source snapshot retrieval timestamp so ingestion freshness reflects the age of the checked-in federal snapshot, not just the newest underlying award date.
