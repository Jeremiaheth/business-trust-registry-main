"""Case queue helpers for the private-lane skeleton."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from models import (
    ALLOWED_CASE_KINDS,
    ALLOWED_CASE_STATES,
    ALLOWED_REFERENCE_KINDS,
    EvidenceReference,
    PrivateCase,
    QueueStatusSnapshot,
)

FORBIDDEN_FIELDS = frozenset(
    {"attachment", "attachments", "binary", "content_bytes", "evidence_file", "file", "files"}
)
OPEN_CASE_STATES = frozenset({"queued", "under_review"})
TRANSITIONS = {
    "queued": frozenset({"rejected", "resolved", "under_review"}),
    "under_review": frozenset({"rejected", "resolved"}),
    "resolved": frozenset(),
    "rejected": frozenset(),
}


class CaseValidationError(ValueError):
    """Raised when a private case document is invalid."""


def create_case(payload: dict[str, object], now: str) -> PrivateCase:
    """Validate and create a new private case record."""
    _reject_forbidden_fields(payload)

    case_id = _require_non_empty_string(payload.get("case_id"), "case_id")
    kind = _require_choice(payload.get("kind"), "kind", ALLOWED_CASE_KINDS)
    redacted_summary = _require_non_empty_string(
        payload.get("redacted_summary"),
        "redacted_summary",
    )
    if len(redacted_summary) < 12:
        raise CaseValidationError("redacted_summary must be at least 12 characters")

    btr_id = payload.get("btr_id")
    if btr_id is not None and (not isinstance(btr_id, str) or not btr_id.strip()):
        raise CaseValidationError("btr_id must be a non-empty string when provided")

    references = _parse_references(payload.get("evidence_references"))
    return PrivateCase(
        case_id=case_id,
        kind=kind,
        state="queued",
        created_at=now,
        updated_at=now,
        redacted_summary=redacted_summary,
        evidence_references=references,
        btr_id=btr_id.strip() if isinstance(btr_id, str) else None,
    )


def transition_case(case: PrivateCase, new_state: str, updated_at: str) -> PrivateCase:
    """Transition a case to its next allowed state."""
    next_state = _require_choice(new_state, "new_state", ALLOWED_CASE_STATES)
    if next_state not in TRANSITIONS[case.state]:
        raise CaseValidationError(
            f"cannot transition case from {case.state} to {next_state}"
        )
    return PrivateCase(
        case_id=case.case_id,
        kind=case.kind,
        state=next_state,
        created_at=case.created_at,
        updated_at=updated_at,
        redacted_summary=case.redacted_summary,
        evidence_references=case.evidence_references,
        btr_id=case.btr_id,
    )


def build_sanitized_public_summary(case: PrivateCase) -> dict[str, object]:
    """Build a public-safe summary document suitable for later audit-plane publication."""
    return {
        "public_summary_version": 1,
        "case_id": case.case_id,
        "kind": case.kind,
        "state": case.state,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "btr_id": case.btr_id,
        "redacted_summary": case.redacted_summary,
        "evidence_references": [
            {
                "kind": reference.kind,
                "value": reference.value,
            }
            for reference in case.evidence_references
        ],
    }


def export_queue_status(cases: list[PrivateCase], generated_at: str) -> QueueStatusSnapshot:
    """Summarize open private-lane queue metrics for later shared safety use."""
    open_cases = [case for case in cases if case.state in OPEN_CASE_STATES]
    kind_counts = Counter(case.kind for case in open_cases)
    state_counts = Counter(case.state for case in open_cases)
    generated = _parse_datetime(generated_at)
    oldest_open_age_days = None

    if open_cases:
        oldest_created_at = min(_parse_datetime(case.created_at) for case in open_cases)
        oldest_open_age_days = max((generated - oldest_created_at).days, 0)

    return QueueStatusSnapshot(
        generated_at=generated_at,
        oldest_open_age_days=oldest_open_age_days,
        open_case_count=len(open_cases),
        open_counts={
            "claims": kind_counts.get("claim", 0),
            "corrections": kind_counts.get("correction", 0),
            "verifications": kind_counts.get("verification", 0),
        },
        states=dict(sorted(state_counts.items())),
    )


def _parse_references(value: object) -> tuple[EvidenceReference, ...]:
    if not isinstance(value, list) or not value:
        raise CaseValidationError("evidence_references must contain at least one item")

    references: list[EvidenceReference] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise CaseValidationError(f"evidence_references[{index}] must be a JSON object")
        _reject_forbidden_fields(item, prefix=f"evidence_references[{index}]")

        kind = _require_choice(
            item.get("kind"),
            f"evidence_references[{index}].kind",
            ALLOWED_REFERENCE_KINDS,
        )
        reference_value = _require_non_empty_string(
            item.get("value"),
            f"evidence_references[{index}].value",
        )

        if kind == "url" and not reference_value.startswith(("http://", "https://")):
            raise CaseValidationError(
                f"evidence_references[{index}].value must start with http:// or https://"
            )
        references.append(EvidenceReference(kind=kind, value=reference_value))
    return tuple(references)


def _reject_forbidden_fields(payload: dict[str, object], prefix: str = "") -> None:
    for forbidden_field in sorted(FORBIDDEN_FIELDS):
        if forbidden_field in payload:
            field_name = f"{prefix}.{forbidden_field}" if prefix else forbidden_field
            raise CaseValidationError(f"{field_name} is not accepted in the private lane")


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaseValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_choice(value: object, field_name: str, choices: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in choices:
        allowed = ", ".join(sorted(choices))
        raise CaseValidationError(f"{field_name} must be one of: {allowed}")
    return value


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
