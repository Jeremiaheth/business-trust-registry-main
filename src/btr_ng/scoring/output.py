"""Typed trust score snapshot output for the scoring engine."""

from __future__ import annotations

from dataclasses import dataclass


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
    evidence_count: int
    generated_at: str
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
            "evidence_count": self.evidence_count,
            "generated_at": self.generated_at,
            "explanation": self.explanation,
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
        }
