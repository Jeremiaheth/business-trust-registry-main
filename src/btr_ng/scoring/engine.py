"""Deterministic Bayesian scoring engine for BTR-NG."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from btr_ng.registry.validator import validate_registry_dir
from btr_ng.safety.models import SafetyReport
from btr_ng.schema import validate_document
from btr_ng.scoring.config import load_scoring_config
from btr_ng.scoring.evidence_mapping import ScoringObservation, map_business_to_observations
from btr_ng.scoring.models import DimensionConfig, ScoringConfig
from btr_ng.scoring.output import DimensionScore, TrustScoreSnapshot


class ScoringEngineError(ValueError):
    """Raised when the scorer cannot build deterministic outputs."""


def score_registry_to_directory(
    registry_dir: Path,
    config_path: Path,
    out_dir: Path,
    safety_report: SafetyReport | None = None,
) -> int:
    """Score the registry and write trust score snapshots to disk."""
    snapshots = score_registry(
        registry_dir=registry_dir,
        config_path=config_path,
        safety_report=safety_report,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    for snapshot in snapshots:
        output_path = out_dir / f"{snapshot.btr_id}.json"
        output_path.write_text(
            json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return len(snapshots)


def score_registry(
    registry_dir: Path,
    config_path: Path,
    safety_report: SafetyReport | None = None,
) -> tuple[TrustScoreSnapshot, ...]:
    """Load registry records and produce deterministic score snapshots."""
    validate_registry_dir(registry_dir)
    config = load_scoring_config(config_path)
    businesses = _load_lane(registry_dir / "businesses")
    evidence_items = _load_lane(registry_dir / "evidence")
    evidence_by_business = _group_evidence_by_business(evidence_items)
    evaluation_at = _determine_evaluation_time(businesses, evidence_items)

    snapshots = tuple(
        score_business(
            business=business,
            evidence_items=evidence_by_business.get(str(business["btr_id"]), []),
            config=config,
            evaluation_at=evaluation_at,
            safety_report=safety_report,
        )
        for business in businesses
    )
    return snapshots


def score_business(
    business: dict[str, object],
    evidence_items: list[dict[str, object]],
    config: ScoringConfig,
    evaluation_at: datetime,
    safety_report: SafetyReport | None = None,
) -> TrustScoreSnapshot:
    """Compute a deterministic trust score snapshot for one business."""
    observations = map_business_to_observations(business, evidence_items)
    grouped_observations = _group_observations_by_dimension(observations)

    dimension_scores: list[DimensionScore] = []
    weighted_score_total = 0.0
    weighted_confidence_total = 0.0
    top_positive: list[tuple[float, str]] = []
    top_negative: list[tuple[float, str]] = []

    for dimension in config.dimensions:
        result = _score_dimension(
            dimension=dimension,
            observations=grouped_observations.get(dimension.name, ()),
            evaluation_at=evaluation_at,
        )
        dimension_scores.append(result)
        weighted_score_total += result.weighted_score
        weighted_confidence_total += dimension.weight * result.confidence

        top_positive.append((result.score, _positive_signal_label(result.name)))
        top_negative.append((1.0 - result.score, _negative_signal_label(result.name)))

    overall_score = round(weighted_score_total, 6)
    if _identity_support_is_weak(grouped_observations.get("identity", ())):
        overall_score = min(overall_score, config.identity_rules.score_cap_without_identity)

    overall_score = max(overall_score, config.identity_rules.score_floor)
    confidence = round(weighted_confidence_total, 6)
    band = _band_for_score(overall_score)

    status = "published"
    if safety_report is not None:
        profile_decision = safety_report.profile_decision(str(business["btr_id"]))
        if profile_decision.force_under_review:
            status = "under_review"
        elif profile_decision.suppress_scoring:
            status = "suppressed"

    snapshot = TrustScoreSnapshot(
        btr_id=str(business["btr_id"]),
        score=round(overall_score, 6),
        confidence=confidence,
        band=band,
        status=status,
        evidence_count=len(evidence_items),
        generated_at=evaluation_at.isoformat().replace("+00:00", "Z"),
        explanation={
            "top_positive_signals": [
                label for _value, label in sorted(top_positive, reverse=True)[:2]
            ],
            "top_negative_signals": [
                label for _value, label in sorted(top_negative, reverse=True)[:2]
            ],
        },
        dimensions=tuple(dimension_scores),
    )
    document = snapshot.to_dict()
    validate_document("trust-score", document)
    return snapshot


def apply_time_decay(
    observed_at: datetime,
    evaluation_at: datetime,
    half_life_days: int,
    max_age_days: int,
) -> float:
    """Return the deterministic time-decay multiplier for an observation."""
    age_days = max(0.0, (evaluation_at - observed_at).total_seconds() / 86400.0)
    if age_days > max_age_days:
        return 0.0
    return float(round(0.5 ** (age_days / half_life_days), 6))


def _score_dimension(
    dimension: DimensionConfig,
    observations: tuple[ScoringObservation, ...],
    evaluation_at: datetime,
) -> DimensionScore:
    success_weight = 0.0
    failure_weight = 0.0
    for observation in observations:
        decay = apply_time_decay(
            observed_at=observation.observed_at,
            evaluation_at=evaluation_at,
            half_life_days=180,
            max_age_days=730,
        )
        success_weight += observation.success_weight * decay
        failure_weight += observation.failure_weight * decay

    posterior_success = dimension.prior.alpha + success_weight
    posterior_total = (
        dimension.prior.alpha + dimension.prior.beta + success_weight + failure_weight
    )
    score = posterior_success / posterior_total
    confidence = (success_weight + failure_weight) / posterior_total
    weighted_score = dimension.weight * score

    return DimensionScore(
        name=dimension.name,
        score=round(score, 6),
        weighted_score=round(weighted_score, 6),
        confidence=round(confidence, 6),
        success_weight=round(success_weight, 6),
        failure_weight=round(failure_weight, 6),
    )


def _group_observations_by_dimension(
    observations: tuple[ScoringObservation, ...],
) -> dict[str, tuple[ScoringObservation, ...]]:
    grouped: dict[str, list[ScoringObservation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.dimension].append(observation)
    return {dimension: tuple(items) for dimension, items in grouped.items()}


def _group_evidence_by_business(
    evidence_items: tuple[dict[str, object], ...],
) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for evidence in evidence_items:
        related_businesses = evidence.get("related_businesses", [])
        if isinstance(related_businesses, list):
            for business_id in related_businesses:
                grouped[str(business_id)].append(evidence)
    return grouped


def _determine_evaluation_time(
    businesses: tuple[dict[str, object], ...],
    evidence_items: tuple[dict[str, object], ...],
) -> datetime:
    timestamps: list[datetime] = [
        _parse_datetime(str(business["updated_at"]))
        for business in businesses
    ]
    timestamps.extend(
        _parse_datetime(str(evidence["recorded_at"]))
        for evidence in evidence_items
    )
    if not timestamps:
        raise ScoringEngineError("cannot determine evaluation time from an empty registry")
    return max(timestamps)


def _load_lane(directory: Path) -> tuple[dict[str, object], ...]:
    if not directory.exists():
        return ()
    documents: list[dict[str, object]] = []
    for file_path in sorted(directory.glob("*.json")):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ScoringEngineError(f"{file_path} must contain a top-level JSON object")
        documents.append(data)
    return tuple(documents)


def _identity_support_is_weak(observations: tuple[ScoringObservation, ...]) -> bool:
    total_identity_success = sum(observation.success_weight for observation in observations)
    return total_identity_success < 1.5


def _band_for_score(score: float) -> str:
    if score >= 0.6:
        return "high"
    if score >= 0.5:
        return "moderate"
    if score >= 0.35:
        return "low"
    return "very_low"


def _positive_signal_label(dimension_name: str) -> str:
    labels = {
        "identity": "identity evidence remains stable",
        "procurement_presence": "procurement-linked evidence is present",
        "evidence_quality": "evidence references are reviewable",
        "manual_verification": "manual verification support is available",
    }
    return labels[dimension_name]


def _negative_signal_label(dimension_name: str) -> str:
    labels = {
        "identity": "identity evidence depth is limited",
        "procurement_presence": "procurement-linked evidence is limited",
        "evidence_quality": "evidence quality remains thin",
        "manual_verification": "manual verification support is limited",
    }
    return labels[dimension_name]


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
