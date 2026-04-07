# Access Matrix

## Public Input Classes

| Input class | Public lane status | Notes |
| --- | --- | --- |
| Business metadata already suitable for public display | Allowed | Stored in `registry/businesses/`. |
| Public evidence links and hashes | Allowed | Prefer links, hashes, and timestamps over copied payloads. |
| Published procurement notices and contract references | Allowed | Procurement signals are derived from published procurement data. |
| Redacted dispute summaries | Allowed | Must stay within fact-correction scope. |
| Time-stamped verification event records | Allowed | Publish only the minimal event metadata needed for traceability. |

## Out of Scope for the Public Lane

| Input class | Public lane status | Notes |
| --- | --- | --- |
| Personal data | Rejected | Must not enter the public repo. |
| Evidence attachments or uploads | Rejected | The public beta remains link-only. |
| Confidential or private documents | Rejected | Use a future private lane, not this repo. |
| Conduct accusations or narrative complaints | Rejected | Public moderation is not a case-management system. |
| Phone-only or offline verification claims | Rejected | Keep machine-access assumptions explicit and narrow. |

## Handling Rules

- CAC and similar registry signals are treated as point-in-time inputs, not continuous truth.
- NOCOPO evidence is complementary and should stay separate from any authority claim.
- When procurement freshness degrades, the public API and site must show the stale state instead of hiding it.
- When disputes are active, the public surface should prefer under-review states over normal scoring.
