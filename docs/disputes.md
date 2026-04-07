# Public Disputes Scope

## Purpose

Public disputes in BTR-NG are correction workflows. They exist to challenge public metadata accuracy, evidence sufficiency, or stale references without opening a public allegations channel.

## Allowed Dispute Inputs

- requests to correct non-sensitive public metadata
- challenges to whether published evidence is sufficient
- replacement public links or hashes
- timestamps or references that show a published source is outdated

## Disallowed Dispute Inputs

- raw evidence uploads
- personal data
- confidential documents
- requests for legal findings
- conduct allegations that require private investigation

## Review Flow

1. Open a dispute record tied to the affected `btr_id`.
2. Mark the profile under review while the case is active.
3. Suppress normal scoring output when the safety controller requires it.
4. Publish only the public-safe dispute summary, timestamps, and references.
5. Resolve the case by updating the profile, evidence set, or dispute state.

## Resolution Guidance

- Close disputes quickly when the correction is objective and public-safe.
- Preserve the audit trail of why a profile moved into or out of under-review status.
- Keep summaries narrow and factual so the public beta stays within fact-correction-only scope.
