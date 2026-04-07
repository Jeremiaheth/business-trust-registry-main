# Private Lane Skeleton

This directory contains the first private-lane skeleton for BTR-NG using Cloudflare Python Workers.

## Scope

The skeleton intentionally exposes only:

- `GET /health`
- `POST /intake/validate`

The intake route is link-only. It accepts URLs, hashes, and redacted summaries. It does not accept binary evidence uploads, attachments, or file payloads.

## Local Development

Cloudflare’s current Python Workers documentation uses `pywrangler`, a `src/entry.py` entrypoint, and the `python_workers` compatibility flag. The local loop is:

```bash
cd private_lane
uv sync
uv run pytest
uv run pywrangler dev
```

If you are authenticated with Cloudflare, deploy with:

```bash
uv run pywrangler deploy
```

## Example Request

```bash
curl --request POST http://localhost:8787/intake/validate \
  --header "Content-Type: application/json" \
  --data '{
    "submission_id": "INTAKE-001",
    "business_reference": "BTR-ACME-001",
    "references": [
      {"kind": "url", "value": "https://example.com/public-source"},
      {"kind": "hash", "value": "0123456789abcdef0123456789abcdef"},
      {"kind": "redacted_summary", "value": "Public-safe redacted intake summary."}
    ]
  }'
```

## Notes

- `private_lane/src/app.py` keeps the request handling pure and locally testable.
- `private_lane/src/entry.py` is the Worker entrypoint used by pywrangler.
- This scaffold is intentionally minimal so it does not open the evidence-upload risk surface before the later private-lane steps exist.
