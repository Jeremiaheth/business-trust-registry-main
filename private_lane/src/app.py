"""Pure request handling for the private-lane worker skeleton."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

MAX_REFERENCES = 10
ALLOWED_REFERENCE_KINDS = frozenset({"hash", "redacted_summary", "url"})
FORBIDDEN_BINARY_FIELDS = frozenset(
    {"attachment", "attachments", "binary", "content_bytes", "evidence_file", "file", "files"}
)
HASH_PATTERN = re.compile(r"^[A-Fa-f0-9]{32,128}$")


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single intake validation issue."""

    field: str
    message: str

    def render(self) -> str:
        """Return a stable human-readable validation error."""
        return f"{self.field}: {self.message}"


class IntakeValidationError(ValueError):
    """Raised when an intake request violates the link-only policy."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.render() for issue in self.issues))


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """A minimal HTTP response model for pure request handling."""

    status: int
    body: str
    headers: dict[str, str]


def validate_intake_payload(payload: object) -> dict[str, object]:
    """Validate and sanitize a link-only intake request."""
    if not isinstance(payload, dict):
        raise IntakeValidationError([ValidationIssue("payload", "must be a JSON object")])

    issues: list[ValidationIssue] = []
    sanitized: dict[str, object] = {}

    for forbidden_field in sorted(FORBIDDEN_BINARY_FIELDS):
        if forbidden_field in payload:
            issues.append(
                ValidationIssue(
                    forbidden_field,
                    "binary evidence uploads are not accepted in the private-lane skeleton",
                )
            )

    submission_id = payload.get("submission_id")
    if not isinstance(submission_id, str) or not submission_id.strip():
        issues.append(ValidationIssue("submission_id", "must be a non-empty string"))
    else:
        sanitized["submission_id"] = submission_id.strip()

    business_reference = payload.get("business_reference")
    if not isinstance(business_reference, str) or not business_reference.strip():
        issues.append(ValidationIssue("business_reference", "must be a non-empty string"))
    else:
        sanitized["business_reference"] = business_reference.strip()

    references = payload.get("references")
    if not isinstance(references, list):
        issues.append(ValidationIssue("references", "must be a JSON array"))
    elif not references:
        issues.append(ValidationIssue("references", "must include at least one reference"))
    elif len(references) > MAX_REFERENCES:
        issues.append(
            ValidationIssue(
                "references",
                f"must not include more than {MAX_REFERENCES} references",
            )
        )
    else:
        sanitized["references"] = _sanitize_references(references, issues)

    if issues:
        raise IntakeValidationError(issues)
    return sanitized


def handle_http_request(
    method: str,
    path: str,
    body_text: str | None = None,
) -> HttpResponse:
    """Handle a minimal private-lane HTTP request."""
    normalized_method = method.upper()

    if path == "/health":
        return _json_response(
            200,
            {
                "status": "ok",
                "service": "btr-ng-private-lane",
                "intake_mode": "link_only",
            },
        )

    if path == "/intake/validate":
        if normalized_method != "POST":
            return _json_response(
                405,
                {
                    "accepted": False,
                    "error": "method_not_allowed",
                    "message": "Use POST for /intake/validate.",
                },
            )

        try:
            payload = json.loads(body_text or "{}")
        except json.JSONDecodeError:
            return _json_response(
                400,
                {
                    "accepted": False,
                    "error": "invalid_json",
                    "message": "Body must be valid JSON.",
                },
            )

        try:
            sanitized = validate_intake_payload(payload)
        except IntakeValidationError as error:
            return _json_response(
                400,
                {
                    "accepted": False,
                    "error": "validation_failed",
                    "issues": [issue.render() for issue in error.issues],
                    "intake_mode": "link_only",
                },
            )

        references = sanitized["references"]
        assert isinstance(references, list)
        kinds = sorted({str(reference["kind"]) for reference in references})
        return _json_response(
            200,
            {
                "accepted": True,
                "business_reference": sanitized["business_reference"],
                "intake_mode": "link_only",
                "reference_count": len(references),
                "reference_kinds": kinds,
                "submission_id": sanitized["submission_id"],
            },
        )

    return _json_response(
        404,
        {
            "accepted": False,
            "error": "not_found",
            "message": "Route not found.",
        },
    )


def _sanitize_references(
    references: list[object],
    issues: list[ValidationIssue],
) -> list[dict[str, str]]:
    sanitized: list[dict[str, str]] = []

    for index, reference in enumerate(references):
        field_prefix = f"references[{index}]"
        if not isinstance(reference, dict):
            issues.append(ValidationIssue(field_prefix, "must be a JSON object"))
            continue

        for forbidden_field in sorted(FORBIDDEN_BINARY_FIELDS):
            if forbidden_field in reference:
                issues.append(
                    ValidationIssue(
                        f"{field_prefix}.{forbidden_field}",
                        "binary evidence uploads are not accepted in the private-lane skeleton",
                    )
                )

        kind = reference.get("kind")
        if not isinstance(kind, str) or kind not in ALLOWED_REFERENCE_KINDS:
            issues.append(
                ValidationIssue(
                    f"{field_prefix}.kind",
                    "must be one of: hash, redacted_summary, url",
                )
            )
            continue

        value = reference.get("value")
        if not isinstance(value, str) or not value.strip():
            issues.append(ValidationIssue(f"{field_prefix}.value", "must be a non-empty string"))
            continue

        normalized_value = value.strip()
        if kind == "url" and not normalized_value.startswith(("http://", "https://")):
            issues.append(
                ValidationIssue(f"{field_prefix}.value", "URL references must start with http:// or https://")
            )
            continue
        if kind == "hash" and not HASH_PATTERN.fullmatch(normalized_value):
            issues.append(
                ValidationIssue(
                    f"{field_prefix}.value",
                    "hash references must be 32 to 128 hexadecimal characters",
                )
            )
            continue
        if kind == "redacted_summary" and len(normalized_value) < 12:
            issues.append(
                ValidationIssue(
                    f"{field_prefix}.value",
                    "redacted summaries must be at least 12 characters",
                )
            )
            continue

        sanitized.append({"kind": kind, "value": normalized_value})

    return sanitized


def _json_response(status: int, document: dict[str, object]) -> HttpResponse:
    return HttpResponse(
        status=status,
        body=json.dumps(document, indent=2, sort_keys=True) + "\n",
        headers={"content-type": "application/json; charset=utf-8"},
    )
