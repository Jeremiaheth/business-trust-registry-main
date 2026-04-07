from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.scoring.config import ScoringConfigError, load_scoring_config, parse_scoring_config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORING_CONFIG_PATH = PROJECT_ROOT / "spec" / "scoring.toml"
runner = CliRunner()


def test_load_valid_scoring_config() -> None:
    config = load_scoring_config(SCORING_CONFIG_PATH)

    assert [dimension.name for dimension in config.dimensions] == [
        "identity",
        "procurement_presence",
        "evidence_quality",
        "manual_verification",
    ]
    assert config.to_dict()["weights_total"] == 1.0
    assert config.identity_rules.score_cap_without_identity == 0.65


def test_parse_scoring_config_rejects_invalid_weights() -> None:
    with pytest.raises(ScoringConfigError) as error:
        parse_scoring_config(
            {
                "dimensions": ["identity", "evidence_quality"],
                "weights": {
                    "identity": 0.6,
                    "evidence_quality": 0.3,
                },
                "beta_priors": {
                    "identity": {"alpha": 2.0, "beta": 2.0},
                    "evidence_quality": {"alpha": 2.0, "beta": 3.0},
                },
                "time_decay": {"half_life_days": 180, "max_age_days": 730},
                "confidence_thresholds": {
                    "insufficient_evidence": 0.35,
                    "publish": 0.7,
                },
                "identity_rules": {
                    "score_floor": 0.1,
                    "score_cap_without_identity": 0.65,
                },
            }
        )

    assert "sum to 1.0" in str(error.value)


def test_parse_scoring_config_rejects_missing_dimension_prior() -> None:
    with pytest.raises(ScoringConfigError) as error:
        parse_scoring_config(
            {
                "dimensions": ["identity", "evidence_quality"],
                "weights": {
                    "identity": 0.5,
                    "evidence_quality": 0.5,
                },
                "beta_priors": {
                    "identity": {"alpha": 2.0, "beta": 2.0},
                },
                "time_decay": {"half_life_days": 180, "max_age_days": 730},
                "confidence_thresholds": {
                    "insufficient_evidence": 0.35,
                    "publish": 0.7,
                },
                "identity_rules": {
                    "score_floor": 0.1,
                    "score_cap_without_identity": 0.65,
                },
            }
        )

    assert "missing beta prior for dimension 'evidence_quality'" in str(error.value)


def test_parse_scoring_config_rejects_bad_threshold_values() -> None:
    with pytest.raises(ScoringConfigError) as error:
        parse_scoring_config(
            {
                "dimensions": ["identity"],
                "weights": {"identity": 1.0},
                "beta_priors": {
                    "identity": {"alpha": 2.0, "beta": 2.0},
                },
                "time_decay": {"half_life_days": 180, "max_age_days": 730},
                "confidence_thresholds": {
                    "insufficient_evidence": 0.8,
                    "publish": 0.7,
                },
                "identity_rules": {
                    "score_floor": 0.1,
                    "score_cap_without_identity": 0.65,
                },
            }
        )

    assert "insufficient_evidence must be less than" in str(error.value)


def test_show_scoring_config_cli_outputs_validated_config() -> None:
    result = runner.invoke(
        app,
        ["show-scoring-config", "--config", str(SCORING_CONFIG_PATH)],
    )

    assert result.exit_code == 0
    assert '"weights_total": 1.0' in result.stdout
    assert '"name": "identity"' in result.stdout
