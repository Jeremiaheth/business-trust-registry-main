"""Map registry records into deterministic scoring observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class ScoringObservation:
    """A weighted success/failure contribution for a scoring dimension."""

    dimension: str
    success_weight: float
    failure_weight: float
    observed_at: datetime
    reason: str


def map_business_to_observations(
    business: dict[str, object],
    evidence_items: list[dict[str, object]],
) -> tuple[ScoringObservation, ...]:
    """Map business and evidence records to deterministic scoring observations."""
    updated_at = _parse_datetime(str(business["updated_at"]))
    identifiers = _require_mapping(business["identifiers"], "identifiers")
    derived_signals = _require_mapping(business["derived_signals"], "derived_signals")
    evidence_count = len(evidence_items)

    observations: list[ScoringObservation] = [
        ScoringObservation(
            dimension="identity",
            success_weight=1.0,
            failure_weight=0.0,
            observed_at=updated_at,
            reason="primary_identifier_present",
        )
    ]

    secondary_identifiers = identifiers.get("secondary")
    if isinstance(secondary_identifiers, list):
        for _secondary_identifier in secondary_identifiers:
            observations.append(
                ScoringObservation(
                    dimension="identity",
                    success_weight=0.5,
                    failure_weight=0.0,
                    observed_at=updated_at,
                    reason="secondary_identifier_present",
                )
            )

    procurement_activity = bool(derived_signals["procurement_activity"])
    manual_verification = bool(derived_signals["manual_verification"])

    if procurement_activity:
        observations.append(
            ScoringObservation(
                dimension="procurement_presence",
                success_weight=1.0,
                failure_weight=0.0,
                observed_at=updated_at,
                reason="business_marked_procurement_activity",
            )
        )
    else:
        observations.append(
            ScoringObservation(
                dimension="procurement_presence",
                success_weight=0.0,
                failure_weight=1.0,
                observed_at=updated_at,
                reason="no_procurement_signal_on_business_record",
            )
        )

    if manual_verification:
        observations.append(
            ScoringObservation(
                dimension="manual_verification",
                success_weight=1.0,
                failure_weight=0.0,
                observed_at=updated_at,
                reason="business_marked_manual_verification",
            )
        )
    else:
        observations.append(
            ScoringObservation(
                dimension="manual_verification",
                success_weight=0.0,
                failure_weight=1.0,
                observed_at=updated_at,
                reason="no_manual_verification_on_business_record",
            )
        )

    if evidence_count < 2:
        observations.append(
            ScoringObservation(
                dimension="evidence_quality",
                success_weight=0.0,
                failure_weight=1.0,
                observed_at=updated_at,
                reason="limited_evidence_count",
            )
        )

    if evidence_count == 0:
        observations.append(
            ScoringObservation(
                dimension="identity",
                success_weight=0.0,
                failure_weight=0.5,
                observed_at=updated_at,
                reason="no_supporting_evidence_items",
            )
        )

    for evidence in evidence_items:
        observations.extend(_map_evidence_item(evidence))

    return tuple(observations)


def _map_evidence_item(evidence: dict[str, object]) -> tuple[ScoringObservation, ...]:
    observed_at = _parse_datetime(str(evidence["observed_at"]))
    source_type = str(evidence["source_type"])
    access = str(evidence["access"])

    observations: list[ScoringObservation] = []

    if source_type == "procurement_notice":
        observations.append(
            ScoringObservation(
                dimension="procurement_presence",
                success_weight=2.0,
                failure_weight=0.0,
                observed_at=observed_at,
                reason="public_procurement_notice",
            )
        )

    if source_type == "manual_verification":
        observations.append(
            ScoringObservation(
                dimension="manual_verification",
                success_weight=1.0,
                failure_weight=0.0,
                observed_at=observed_at,
                reason="manual_verification_reference",
            )
        )
        observations.append(
            ScoringObservation(
                dimension="identity",
                success_weight=0.75,
                failure_weight=0.0,
                observed_at=observed_at,
                reason="manual_verification_supports_identity",
            )
        )

    if source_type == "registry_extract":
        observations.append(
            ScoringObservation(
                dimension="identity",
                success_weight=0.75,
                failure_weight=0.0,
                observed_at=observed_at,
                reason="registry_extract_supports_identity",
            )
        )

    if access == "public_reference":
        observations.append(
            ScoringObservation(
                dimension="evidence_quality",
                success_weight=0.9,
                failure_weight=0.0,
                observed_at=observed_at,
                reason="public_reference_available",
            )
        )
    else:
        observations.append(
            ScoringObservation(
                dimension="evidence_quality",
                success_weight=0.6,
                failure_weight=0.0,
                observed_at=observed_at,
                reason="restricted_reference_available",
            )
        )

    return tuple(observations)


def _require_mapping(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
