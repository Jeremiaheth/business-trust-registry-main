"""Command-line interface for BTR-NG."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from btr_ng import __version__
from btr_ng.policy.validate import OpsValidationError, validate_ops_dir
from btr_ng.publishing.api_builder import ApiBuildError, build_public_api
from btr_ng.registry.validator import RegistryValidationError, validate_registry_dir
from btr_ng.safety.controller import (
    build_safety_report,
    load_runtime_safety_inputs,
)
from btr_ng.scoring.config import ScoringConfigError, load_scoring_config
from btr_ng.scoring.engine import ScoringEngineError, score_registry_to_directory
from btr_ng.site_builder.builder import SiteBuildError, build_site

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

BUILD_API_SCORE_DIR_OPTION = typer.Option(
    Path("build") / "scores",
    "--scores",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Directory that contains trust score snapshot JSON files.",
)

DERIVED_DIR_OPTION = typer.Option(
    Path("derived"),
    "--derived",
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
    help="Directory that contains derived JSON artifacts to publish when present.",
)

API_OUTPUT_DIR_OPTION = typer.Option(
    Path("public") / "api" / "v1",
    "--out",
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
    help="Directory where static public API artifacts will be written.",
)

SITE_API_DIR_OPTION = typer.Option(
    Path("public") / "api" / "v1",
    "--api",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Directory that contains generated static API artifacts.",
)

SITE_TEMPLATE_DIR_OPTION = typer.Option(
    Path("site") / "templates",
    "--templates",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Directory that contains Jinja templates for the static site.",
)

SITE_STATIC_DIR_OPTION = typer.Option(
    Path("site") / "static",
    "--static-dir",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Directory that contains static site assets.",
)

SITE_OUTPUT_DIR_OPTION = typer.Option(
    Path("site") / "dist",
    "--out",
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
    help="Directory where generated static HTML files will be written.",
)

INGESTION_STATUS_OPTION = typer.Option(
    "healthy",
    "--ingestion-status",
    help="Procurement ingestion status: healthy, stale, or failed.",
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
    ops_dir: Path = OPS_DIR_OPTION,
    ingestion_status: str = INGESTION_STATUS_OPTION,
) -> None:
    """Score the registry and write trust score snapshots to disk."""
    try:
        validate_registry_dir(registry_dir)
        runtime_inputs = load_runtime_safety_inputs(
            registry_dir=registry_dir,
            ops_dir=ops_dir,
            ingestion_status=ingestion_status,
        )
        safety_report = build_safety_report(runtime_inputs)
        written = score_registry_to_directory(
            registry_dir=registry_dir,
            config_path=config_path,
            out_dir=out_dir,
            safety_report=safety_report,
        )
    except (RegistryValidationError, ScoringEngineError, ScoringConfigError, ValueError) as error:
        if isinstance(error, RegistryValidationError):
            for issue in error.issues:
                typer.echo(issue.render())
        else:
            typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"score output written: {out_dir} ({written} snapshots)")


@app.command("safety-report")
def safety_report(
    registry_dir: Path = SCORE_REGISTRY_OPTION,
    ops_dir: Path = OPS_DIR_OPTION,
    ingestion_status: str = INGESTION_STATUS_OPTION,
) -> None:
    """Build and print the deterministic runtime safety report."""
    try:
        runtime_inputs = load_runtime_safety_inputs(
            registry_dir=registry_dir,
            ops_dir=ops_dir,
            ingestion_status=ingestion_status,
        )
        report = build_safety_report(runtime_inputs)
    except ValueError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(json.dumps(report.to_dict(), indent=2, sort_keys=True))


@app.command("build-api")
def build_api(
    registry_dir: Path = SCORE_REGISTRY_OPTION,
    score_dir: Path = BUILD_API_SCORE_DIR_OPTION,
    derived_dir: Path = DERIVED_DIR_OPTION,
    out_dir: Path = API_OUTPUT_DIR_OPTION,
) -> None:
    """Build static public API artifacts from scored registry inputs."""
    try:
        written = build_public_api(
            registry_dir=registry_dir,
            score_dir=score_dir,
            out_dir=out_dir,
            derived_dir=derived_dir,
        )
    except ApiBuildError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"public API written: {out_dir} ({written} artifacts)")


@app.command("build-site")
def build_static_site(
    api_dir: Path = SITE_API_DIR_OPTION,
    template_dir: Path = SITE_TEMPLATE_DIR_OPTION,
    static_dir: Path = SITE_STATIC_DIR_OPTION,
    out_dir: Path = SITE_OUTPUT_DIR_OPTION,
) -> None:
    """Render the static public site from generated API artifacts."""
    try:
        written = build_site(
            api_dir=api_dir,
            out_dir=out_dir,
            template_dir=template_dir,
            static_dir=static_dir,
        )
    except SiteBuildError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"site written: {out_dir} ({written} pages)")


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
