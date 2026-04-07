"""Command-line interface for BTR-NG."""

from __future__ import annotations

from pathlib import Path

import typer

from btr_ng import __version__
from btr_ng.policy.validate import OpsValidationError, validate_ops_dir
from btr_ng.registry.validator import RegistryValidationError, validate_registry_dir

app = typer.Typer(
    add_completion=False,
    help="BTR-NG developer CLI.",
    no_args_is_help=True,
)

OPS_DIR_OPTION = typer.Option(
    Path("ops"),
    "--ops-dir",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help=(
        "Directory that contains owners.yml, policy_gates.yml, "
        "safety_policy.json, and privacy_posture.json."
    ),
)

REGISTRY_DIR_OPTION = typer.Option(
    Path("registry"),
    "--registry-dir",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Directory that contains registry JSON records.",
)


@app.callback()
def main_callback() -> None:
    """Provide a group entrypoint so commands remain explicit subcommands."""


@app.command("version")
def version() -> None:
    """Print the installed package version."""
    typer.echo(__version__)


@app.command("validate-ops")
def validate_ops(
    ops_dir: Path = OPS_DIR_OPTION,
) -> None:
    """Validate policy and governance configuration."""
    try:
        validate_ops_dir(ops_dir)
    except OpsValidationError as error:
        for issue in error.issues:
            typer.echo(issue.render())
        raise typer.Exit(code=1) from error

    typer.echo(f"ops configuration valid: {ops_dir}")


@app.command("validate-registry")
def validate_registry(
    registry_dir: Path = REGISTRY_DIR_OPTION,
) -> None:
    """Validate seeded registry records against canonical schemas."""
    try:
        validated_files = validate_registry_dir(registry_dir)
    except RegistryValidationError as error:
        for issue in error.issues:
            typer.echo(issue.render())
        raise typer.Exit(code=1) from error

    typer.echo(
        f"registry valid: {registry_dir} ({validated_files} JSON files checked)"
    )


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
