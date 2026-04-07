"""Typed internal models for scoring configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BetaPrior:
    """Bayesian prior parameters for a scoring dimension."""

    alpha: float
    beta: float

    def to_dict(self) -> dict[str, float]:
        """Return a JSON-serializable representation."""
        return {"alpha": self.alpha, "beta": self.beta}


@dataclass(frozen=True, slots=True)
class DimensionConfig:
    """Typed scoring configuration for a single dimension."""

    name: str
    weight: float
    prior: BetaPrior

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "name": self.name,
            "weight": self.weight,
            "prior": self.prior.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class TimeDecayConfig:
    """Time-decay parameters used by the future scorer."""

    half_life_days: int
    max_age_days: int

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-serializable representation."""
        return {
            "half_life_days": self.half_life_days,
            "max_age_days": self.max_age_days,
        }


@dataclass(frozen=True, slots=True)
class ConfidenceThresholds:
    """Confidence thresholds used by future display gating."""

    insufficient_evidence: float
    publish: float

    def to_dict(self) -> dict[str, float]:
        """Return a JSON-serializable representation."""
        return {
            "insufficient_evidence": self.insufficient_evidence,
            "publish": self.publish,
        }


@dataclass(frozen=True, slots=True)
class IdentityRules:
    """Identity-based score floor and cap rules."""

    score_floor: float
    score_cap_without_identity: float

    def to_dict(self) -> dict[str, float]:
        """Return a JSON-serializable representation."""
        return {
            "score_floor": self.score_floor,
            "score_cap_without_identity": self.score_cap_without_identity,
        }


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """Full validated scoring configuration."""

    dimensions: tuple[DimensionConfig, ...]
    time_decay: TimeDecayConfig
    confidence_thresholds: ConfidenceThresholds
    identity_rules: IdentityRules

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
            "weights_total": round(sum(dimension.weight for dimension in self.dimensions), 6),
            "time_decay": self.time_decay.to_dict(),
            "confidence_thresholds": self.confidence_thresholds.to_dict(),
            "identity_rules": self.identity_rules.to_dict(),
        }
