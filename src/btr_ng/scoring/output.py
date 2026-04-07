"""Typed trust score snapshot output for the scoring engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DisplayStateName = Literal["normal", "insufficient_evidence", "under_review", "maintenance"]


@dataclass(frozen=True, slots=True)
class DimensionScore:
    """Per-dimension score details."""

    name: str
    score: float
    weighted_score: float
    confidence: float
    success_weight: float
    failure_weight: float

    def to_dict(self) -> dict[str, float | str]:
        """Return a JSON-serializable representation."""
        return {
            "name": self.name,
            "score": self.score,
            "weighted_score": self.weighted_score,
            "confidence": self.confidence,
            "success_weight": self.success_weight,
            "failure_weight": self.failure_weight,
        }


@dataclass(frozen=True, slots=True)
class TrustScoreSnapshot:
    """TrustScoreSnapshot-shaped document emitted by the scorer."""

    btr_id: str
    score: float
    confidence: float
    band: str
    status: str
    display_state: DisplayStateName
    evidence_count: int
    generated_at: str
    verification_timestamp: str
    public_note: str
    explanation: dict[str, list[str]]
    dimensions: tuple[DimensionScore, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the JSON document to persist."""
        return {
            "btr_id": self.btr_id,
            "score": self.score,
            "confidence": self.confidence,
            "band": self.band,
            "status": self.status,
            "display_state": self.display_state,
            "evidence_count": self.evidence_count,
            "generated_at": self.generated_at,
            "verification_timestamp": self.verification_timestamp,
            "public_note": self.public_note,
            "explanation": self.explanation,
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
        }
