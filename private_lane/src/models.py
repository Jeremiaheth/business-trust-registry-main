"""Typed models for the private-lane case queue."""

from __future__ import annotations

from dataclasses import dataclass

ALLOWED_CASE_KINDS = frozenset({"claim", "correction", "verification"})
ALLOWED_CASE_STATES = frozenset({"queued", "under_review", "resolved", "rejected"})
ALLOWED_REFERENCE_KINDS = frozenset({"hash", "url"})


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """A link-only evidence reference for a private case."""

    kind: str
    value: str


@dataclass(frozen=True, slots=True)
class PrivateCase:
    """Structured queue record for a private-lane case."""

    case_id: str
    kind: str
    state: str
    created_at: str
    updated_at: str
    redacted_summary: str
    evidence_references: tuple[EvidenceReference, ...]
    btr_id: str | None = None


@dataclass(frozen=True, slots=True)
class QueueStatusSnapshot:
    """Queue metrics that can later feed shared safety logic."""

    generated_at: str
    oldest_open_age_days: int | None
    open_case_count: int
    open_counts: dict[str, int]
    states: dict[str, int]
