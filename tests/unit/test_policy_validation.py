from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.policy.validate import OpsValidationError, validate_ops_dir

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "ops"
runner = CliRunner()


def test_validate_ops_accepts_safe_defaults() -> None:
    config = validate_ops_dir(FIXTURES_DIR / "valid")

    assert config.policy_gates.enable_evidence_uploads is False
    assert config.privacy_posture.public_repo_accepts_personal_data is False


def test_validate_ops_rejects_missing_required_owner() -> None:
    with pytest.raises(OpsValidationError) as error:
        validate_ops_dir(FIXTURES_DIR / "invalid_missing_owner")

    rendered = [issue.render() for issue in error.value.issues]
    assert any(
        "required owner 'verifier_approvals' must be assigned" in issue
        for issue in rendered
    )
    assert any("enable_verifier_programme" in issue for issue in rendered)


def test_validate_ops_rejects_privacy_posture_conflict() -> None:
    with pytest.raises(OpsValidationError) as error:
        validate_ops_dir(FIXTURES_DIR / "invalid_privacy_conflict")

    rendered = [issue.render() for issue in error.value.issues]
    assert any("public evidence upload posture must match" in issue for issue in rendered)


def test_validate_ops_cli_reports_success() -> None:
    result = runner.invoke(app, ["validate-ops", "--ops-dir", str(FIXTURES_DIR / "valid")])

    assert result.exit_code == 0
    assert "ops configuration valid" in result.stdout


def test_validate_ops_cli_reports_errors() -> None:
    result = runner.invoke(
        app,
        ["validate-ops", "--ops-dir", str(FIXTURES_DIR / "invalid_privacy_conflict")],
    )

    assert result.exit_code == 1
    assert "privacy_posture.json" in result.stdout
