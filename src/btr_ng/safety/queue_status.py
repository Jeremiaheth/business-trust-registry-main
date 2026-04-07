"""Queue status artifact helpers for the public beta."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from btr_ng.registry.disputes import load_dispute_records
from btr_ng.safety.models import QueueSnapshot, SafetyReport
from btr_ng.schema import validate_document


@dataclass(frozen=True, slots=True)
class QueueStatusArtifact:
    """Published queue status document."""

    generated_at: str
    mode: str
    stale: bool
    open_counts: dict[str, int]
    oldest_open_age_days: int | None
    message: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable document."""
        document: dict[str, object] = {
            "generated_at": self.generated_at,
            "mode": self.mode,
            "stale": self.stale,
            "open_counts": self.open_counts,
            "message": self.message,
        }
        if self.oldest_open_age_days is not None:
            document["oldest_open_age_days"] = self.oldest_open_age_days
        return document


def build_queue_status_artifact(
    registry_dir: Path,
    generated_at: str,
    safety_report: SafetyReport,
    stale_override: bool | None = None,
) -> QueueStatusArtifact:
    """Build a deterministic queue-status artifact."""
    generated_at_dt = _parse_datetime(generated_at)
    oldest_open_age_days = _oldest_open_age_days(registry_dir, generated_at_dt)
    mode = _queue_mode_for_report(safety_report)
    artifact = QueueStatusArtifact(
        generated_at=generated_at,
        mode=mode,
        stale=(
            stale_override
            if stale_override is not None
            else safety_report.procurement_signals_stale
        ),
        open_counts={
            "claims": safety_report.queue.claims,
            "corrections": safety_report.queue.corrections,
            "disputes": safety_report.queue.disputes,
            "verifications": safety_report.queue.verifications,
        },
        oldest_open_age_days=oldest_open_age_days,
        message=_queue_message_for_report(safety_report, mode),
    )
    validate_document("queue-status", artifact.to_dict())
    return artifact


def evaluate_queue_mode(
    queue: QueueSnapshot,
    backlog_warning_threshold: int,
    maintenance_mode_threshold: int,
) -> str:
    """Return queue mode from objective backlog thresholds."""
    if queue.total_open >= maintenance_mode_threshold:
        return "maintenance"
    if queue.total_open >= backlog_warning_threshold:
        return "degraded"
    return "normal"


def _queue_mode_for_report(report: SafetyReport) -> str:
    if report.system_mode == "MAINTENANCE":
        return "maintenance"
    if any("Backlog is elevated" in message for message in report.public_banner_messages):
        return "degraded"
    return "normal"


def _queue_message_for_report(report: SafetyReport, mode: str) -> str:
    if mode == "maintenance":
        return "Backlog is above maintenance threshold. Scoring may be suppressed under load."
    if mode == "degraded":
        return "Backlog is elevated. Scoring may be suppressed under load."
    return "Queue is within normal operating thresholds."


def _oldest_open_age_days(registry_dir: Path, generated_at: datetime) -> int | None:
    disputes = [
        record
        for record in load_dispute_records(registry_dir / "disputes")
        if record.is_active
    ]
    if not disputes:
        return None
    oldest_opened_at = min(_parse_datetime(record.opened_at) for record in disputes)
    age_days = int((generated_at - oldest_opened_at).total_seconds() // 86400)
    return max(age_days, 0)


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
