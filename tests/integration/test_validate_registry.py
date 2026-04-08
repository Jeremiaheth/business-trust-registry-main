from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.registry.validator import RegistryValidationError, validate_registry_dir

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
INVALID_FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "registry_invalid"
runner = CliRunner()


def test_seed_registry_validates_end_to_end() -> None:
    validated_files = validate_registry_dir(REGISTRY_DIR)

    assert validated_files == 40


def test_invalid_registry_fixture_names_file_and_schema_path() -> None:
    with pytest.raises(RegistryValidationError) as error:
        validate_registry_dir(INVALID_FIXTURE_DIR)

    rendered = [issue.render() for issue in error.value.issues]
    assert any("bad-business.json" in issue for issue in rendered)
    assert any("record_state" in issue for issue in rendered)
    assert any("business-record" in issue for issue in rendered)


def test_validate_registry_cli_reports_success() -> None:
    result = runner.invoke(app, ["validate-registry", "--registry-dir", str(REGISTRY_DIR)])

    assert result.exit_code == 0
    assert "registry valid" in result.stdout


def test_validate_registry_cli_reports_failure() -> None:
    result = runner.invoke(
        app,
        ["validate-registry", "--registry-dir", str(INVALID_FIXTURE_DIR)],
    )

    assert result.exit_code == 1
    assert "bad-business.json" in result.stdout
    assert "record_state" in result.stdout
