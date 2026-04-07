"""Load and validate machine-readable scoring configuration."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from btr_ng.scoring.models import (
    BetaPrior,
    ConfidenceThresholds,
    DimensionConfig,
    IdentityRules,
    ScoringConfig,
    TimeDecayConfig,
)


class ScoringConfigError(ValueError):
    """Raised when scoring configuration is invalid."""


def load_scoring_config(path: Path) -> ScoringConfig:
    """Load and validate scoring configuration from disk."""
    try:
        raw_data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ScoringConfigError(f"missing scoring config: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ScoringConfigError(f"failed to parse {path.name}: {error}") from error

    if not isinstance(raw_data, dict):
        raise ScoringConfigError(f"{path.name} must contain a top-level table")
    return parse_scoring_config(raw_data)


def parse_scoring_config(raw_data: Mapping[str, Any]) -> ScoringConfig:
    """Validate scoring configuration from an in-memory mapping."""
    dimension_names = _require_string_list(raw_data, "dimensions")
    weights = _require_table(raw_data, "weights")
    beta_priors = _require_table(raw_data, "beta_priors")
    time_decay_table = _require_table(raw_data, "time_decay")
    threshold_table = _require_table(raw_data, "confidence_thresholds")
    identity_table = _require_table(raw_data, "identity_rules")

    dimensions = tuple(
        _build_dimension_config(name, weights, beta_priors)
        for name in dimension_names
    )

    _validate_weights(dimensions)
    _validate_declared_keys(dimension_names, weights, beta_priors)

    time_decay = TimeDecayConfig(
        half_life_days=_require_positive_int(time_decay_table, "half_life_days"),
        max_age_days=_require_positive_int(time_decay_table, "max_age_days"),
    )
    if time_decay.max_age_days <= time_decay.half_life_days:
        raise ScoringConfigError(
            "time_decay.max_age_days must be greater than time_decay.half_life_days"
        )

    confidence_thresholds = ConfidenceThresholds(
        insufficient_evidence=_require_probability(
            threshold_table, "insufficient_evidence"
        ),
        publish=_require_probability(threshold_table, "publish"),
    )
    if confidence_thresholds.insufficient_evidence >= confidence_thresholds.publish:
        raise ScoringConfigError(
            "confidence_thresholds.insufficient_evidence must be less than "
            "confidence_thresholds.publish"
        )

    identity_rules = IdentityRules(
        score_floor=_require_probability(identity_table, "score_floor"),
        score_cap_without_identity=_require_probability(
            identity_table, "score_cap_without_identity"
        ),
    )
    if identity_rules.score_floor > identity_rules.score_cap_without_identity:
        raise ScoringConfigError(
            "identity_rules.score_floor must be less than or equal to "
            "identity_rules.score_cap_without_identity"
        )

    return ScoringConfig(
        dimensions=dimensions,
        time_decay=time_decay,
        confidence_thresholds=confidence_thresholds,
        identity_rules=identity_rules,
    )


def _build_dimension_config(
    name: str,
    weights: Mapping[str, Any],
    beta_priors: Mapping[str, Any],
) -> DimensionConfig:
    if name not in weights:
        raise ScoringConfigError(f"missing weight for dimension '{name}'")
    if name not in beta_priors:
        raise ScoringConfigError(f"missing beta prior for dimension '{name}'")

    weight = _require_probability(weights, name)
    prior_table = _require_table(beta_priors, name)
    prior = BetaPrior(
        alpha=_require_positive_number(prior_table, "alpha"),
        beta=_require_positive_number(prior_table, "beta"),
    )
    return DimensionConfig(name=name, weight=weight, prior=prior)


def _validate_weights(dimensions: tuple[DimensionConfig, ...]) -> None:
    total = sum(dimension.weight for dimension in dimensions)
    if abs(total - 1.0) > 1e-9:
        raise ScoringConfigError(f"dimension weights must sum to 1.0, got {total:.6f}")


def _validate_declared_keys(
    dimension_names: tuple[str, ...],
    weights: Mapping[str, Any],
    beta_priors: Mapping[str, Any],
) -> None:
    declared = set(dimension_names)
    extra_weights = sorted(set(weights) - declared)
    extra_priors = sorted(set(beta_priors) - declared)

    if extra_weights:
        raise ScoringConfigError(
            f"weights contain undeclared dimensions: {', '.join(extra_weights)}"
        )
    if extra_priors:
        raise ScoringConfigError(
            f"beta_priors contain undeclared dimensions: {', '.join(extra_priors)}"
        )


def _require_table(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise ScoringConfigError(f"'{key}' must be a TOML table")
    return value


def _require_string_list(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ScoringConfigError(f"'{key}' must be an array of strings")
    cleaned = tuple(item.strip() for item in value)
    if not cleaned or any(not item for item in cleaned):
        raise ScoringConfigError(f"'{key}' must contain at least one non-empty dimension name")
    if len(set(cleaned)) != len(cleaned):
        raise ScoringConfigError(f"'{key}' must not contain duplicate dimension names")
    return cleaned


def _require_probability(data: Mapping[str, Any], key: str) -> float:
    value = _require_number(data, key)
    if not 0.0 <= value <= 1.0:
        raise ScoringConfigError(f"'{key}' must be between 0.0 and 1.0")
    return value


def _require_positive_number(data: Mapping[str, Any], key: str) -> float:
    value = _require_number(data, key)
    if value <= 0:
        raise ScoringConfigError(f"'{key}' must be greater than zero")
    return value


def _require_positive_int(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ScoringConfigError(f"'{key}' must be a positive integer")
    return value


def _require_number(data: Mapping[str, Any], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ScoringConfigError(f"'{key}' must be a number")
    return float(value)
