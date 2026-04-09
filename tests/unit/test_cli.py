from typer.testing import CliRunner

from btr_ng import __version__
from btr_ng.cli import app

runner = CliRunner()


def test_cli_help_shows_usage() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "BTR-NG developer CLI." in result.stdout
    assert "package-cloudflare-pages" in result.stdout
    assert "version" in result.stdout
    assert "validate-seed-sources" in result.stdout


def test_cli_version_command_prints_package_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__
