# Privacy

## Public by Design

This repository is a public read plane. The following data classes are intentionally public:

- public business profile metadata
- public evidence references, hashes, and source links
- time-stamped verification event data
- dispute summaries that stay within the fact-correction scope
- scores, confidence values, queue state, and procurement freshness markers

## Not Accepted

The public beta must reject the following:

- personal data
- attachments or evidence file uploads
- confidential documents
- private contact records
- narrative complaints that are outside fact correction

Issue forms and moderation guidance keep the public lane link-only. Operators should accept URLs, hashes, and redacted summaries only.

## Retention Stance

- Public repo content is durable by default because Git history is replicated and forkable.
- Generated API and site artifacts can be rebuilt and replaced from repository state.
- Unsafe content that slips in should be removed from the current branch quickly, but operators must not promise complete erasure from every clone or cache.

## Correction Stance

- Corrections are preferred over silent deletion when the data is public-safe and the dispute is about accuracy or evidence sufficiency.
- Active disputes should move the affected profile into an under-review path until the fact-correction case is closed.
- Public summaries should stay based on available verified evidence and should not expand into private adjudication.

## Operator Expectations

- Do not request raw evidence packs in the public repo.
- Do not ask reporters to post personal data.
- Treat every public record as a minimal, reviewable evidence dossier rather than a full case file.
