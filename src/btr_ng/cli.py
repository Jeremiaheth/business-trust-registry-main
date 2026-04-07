"""Command-line interface for BTR-NG."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from btr_ng import __version__
from btr_ng.policy.validate import OpsValidationError, validate_ops_dir
from btr_ng.registry.validator import RegistryValidationError, validate_registry_dir
from btr_ng.scoring.config import ScoringConfigError, load_scoring_config
from btr_ng.scoring.engine import ScoringEngineError, score_registry_to_directory

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

SCORE_REGISTRY_OPTION = typer.Option(
    Path("registry"),
    "--registry",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Directory that contains registry JSON records for scoring.",
)

SCORING_CONFIG_OPTION = typer.Option(
    Path("spec") / "scoring.toml",
    "--config",
    file_okay=True,
    dir_okay=False,
    readable=True,
    resolve_path=True,
    help="Path to the machine-readable scoring configuration TOML file.",
)

SCORE_OUTPUT_DIR_OPTION = typer.Option(
    Path("build") / "scores",
    "--out",
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
    help="Directory where trust score snapshot JSON files will be written.",
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


@app.command("show-scoring-config")
def show_scoring_config(
    config_path: Path = SCORING_CONFIG_OPTION,
) -> None:
    """Load, validate, and print the scoring configuration."""
    try:
        config = load_scoring_config(config_path)
    except ScoringConfigError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(json.dumps(config.to_dict(), indent=2, sort_keys=True))


@app.command("score")
def score(
    registry_dir: Path = SCORE_REGISTRY_OPTION,
    out_dir: Path = SCORE_OUTPUT_DIR_OPTION,
    config_path: Path = SCORING_CONFIG_OPTION,
) -> None:
    """Score the registry and write trust score snapshots to disk."""
    try:
        validate_registry_dir(registry_dir)
        written = score_registry_to_directory(
            registry_dir=registry_dir,
            config_path=config_path,
            out_dir=out_dir,
        )
    except (RegistryValidationError, ScoringEngineError, ScoringConfigError) as error:
        if isinstance(error, RegistryValidationError):
            for issue in error.issues:
                typer.echo(issue.render())
        else:
            typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"score output written: {out_dir} ({written} snapshots)")


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
