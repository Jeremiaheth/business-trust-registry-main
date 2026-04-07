# Security Policy

## Reporting

Do not open public issues for security-sensitive problems. Contact the project maintainer privately once the dedicated security and incident-response channels are defined in repository policy files.

## Public Repository Boundary

- Do not commit secrets.
- Do not commit personal data.
- Do not upload raw evidence or identity documents.

## Baseline Verification

Run the local checks before pushing changes:

```powershell
pytest -q
ruff check .
mypy src
```
