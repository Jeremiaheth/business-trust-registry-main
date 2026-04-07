"""Typed models for runtime safety decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from btr_ng.policy.config import OpsConfig

SystemModeName = Literal["NORMAL", "MAINTENANCE", "SHUTDOWN"]
IngestionStatusName = Literal["healthy", "stale", "failed"]


@dataclass(frozen=True, slots=True)
class QueueSnapshot:
    """Runtime queue counts available to the safety controller."""

    claims: int
    corrections: int
    disputes: int
    verifications: int

    @property
    def total_open(self) -> int:
        """Return total open work items."""
        return self.claims + self.corrections + self.disputes + self.verifications

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-serializable representation."""
        return {
            "claims": self.claims,
            "corrections": self.corrections,
            "disputes": self.disputes,
            "verifications": self.verifications,
            "total_open": self.total_open,
        }


@dataclass(frozen=True, slots=True)
class RuntimeSafetyInputs:
    """Objective inputs consumed by the safety controller."""

    ops_config: OpsConfig
    queue: QueueSnapshot
    active_disputes: tuple[str, ...]
    active_dispute_updates: dict[str, str]
    ingestion_status: IngestionStatusName


@dataclass(frozen=True, slots=True)
class ProfileSafetyDecision:
    """Per-profile safety decision derived from the system safety report."""

    force_under_review: bool
    suppress_scoring: bool
    review_timestamp: str | None
    public_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "force_under_review": self.force_under_review,
            "suppress_scoring": self.suppress_scoring,
            "review_timestamp": self.review_timestamp,
            "public_notes": list(self.public_notes),
        }


@dataclass(frozen=True, slots=True)
class SafetyReport:
    """Runtime safety decision bundle."""

    system_mode: SystemModeName
    scoring_enabled: bool
    evidence_uploads_enabled: bool
    verifier_programme_enabled: bool
    procurement_signals_stale: bool
    active_disputes: tuple[str, ...]
    active_dispute_updates: dict[str, str]
    queue: QueueSnapshot
    public_banner_messages: tuple[str, ...]

    def profile_decision(self, btr_id: str) -> ProfileSafetyDecision:
        """Return the per-profile safety decision for a business."""
        notes: list[str] = []
        force_under_review = False
        suppress_scoring = False

        if btr_id in self.active_disputes:
            force_under_review = True
            suppress_scoring = True
            notes.append("Profile is under review while a fact-correction case is open.")
        review_timestamp = self.active_dispute_updates.get(btr_id)

        if not self.scoring_enabled:
            suppress_scoring = True
            notes.append("Scoring is temporarily suppressed by system safety mode.")

        if self.procurement_signals_stale:
            notes.append("Procurement-linked signals are stale pending ingestion recovery.")

        return ProfileSafetyDecision(
            force_under_review=force_under_review,
            suppress_scoring=suppress_scoring,
            review_timestamp=review_timestamp,
            public_notes=tuple(notes),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "system_mode": self.system_mode,
            "scoring_enabled": self.scoring_enabled,
            "evidence_uploads_enabled": self.evidence_uploads_enabled,
            "verifier_programme_enabled": self.verifier_programme_enabled,
            "procurement_signals_stale": self.procurement_signals_stale,
            "active_disputes": list(self.active_disputes),
            "active_dispute_updates": self.active_dispute_updates,
            "queue": self.queue.to_dict(),
            "public_banner_messages": list(self.public_banner_messages),
        }
