"""Command-line interface for BTR-NG."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from btr_ng import __version__
from btr_ng.deploy import CloudflarePagesPackageError, package_cloudflare_pages
from btr_ng.ingestion.nocopo import IngestionError, ingest_nocopo_fixture
from btr_ng.ingestion.quality import IngestionQualityError, build_nocopo_quality_report
from btr_ng.policy.validate import OpsValidationError, validate_ops_dir
from btr_ng.publishing.api_builder import ApiBuildError, build_public_api
from btr_ng.registry.validator import RegistryValidationError, validate_registry_dir
from btr_ng.release import ManifestVerificationError, verify_release_manifest
from btr_ng.repo_safety.copy_linter import CopyLintError, lint_project_copy
from btr_ng.repo_safety.pii_scanner import RepoSafetyError, scan_repo_safety
from btr_ng.safety.controller import (
    build_safety_report,
    load_runtime_safety_inputs,
)
from btr_ng.scoring.config import ScoringConfigError, load_scoring_config
from btr_ng.scoring.engine import ScoringEngineError, score_registry_to_directory
from btr_ng.seeding import RealSeedError, generate_real_seed, validate_seed_sources
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

DERIVED_REPORTS_DIR_OPTION = typer.Option(
    Path("derived") / "reports",
    "--out",
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
    help="Directory where derived ingestion quality reports will be written.",
)

DERIVED_NOCOPO_DIR_OPTION = typer.Option(
    Path("derived") / "nocopo",
    "--derived",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Directory that contains derived NOCOPO supplier summaries.",
)

INGEST_NOCOPO_OUTPUT_DIR_OPTION = typer.Option(
    Path("derived") / "nocopo",
    "--out",
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
    help="Directory where derived NOCOPO supplier summaries will be written.",
)

INGEST_NOCOPO_INPUT_PATH_OPTION = typer.Option(
    ...,
    "--input",
    file_okay=True,
    dir_okay=False,
    readable=True,
    resolve_path=True,
    help="Path to a local NOCOPO/OCDS JSON fixture file.",
)

MAX_AGE_DAYS_OPTION = typer.Option(
    30,
    "--max-age-days",
    min=1,
    help="Maximum procurement source age in days before stale markers are applied.",
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

PAGES_PACKAGE_SITE_DIR_OPTION = typer.Option(
    Path("site") / "dist",
    "--site-dir",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Directory that contains generated static HTML pages for Cloudflare Pages packaging.",
)

PAGES_PACKAGE_API_DIR_OPTION = typer.Option(
    Path("public") / "api" / "v1",
    "--api-dir",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help=(
        "Directory that contains generated static public API artifacts "
        "for Cloudflare Pages packaging."
    ),
)

PAGES_PACKAGE_OUT_DIR_OPTION = typer.Option(
    Path("build") / "cloudflare" / "pages",
    "--out",
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
    help="Directory where the merged Cloudflare Pages deploy artifact will be written.",
)

PROJECT_ROOT_OPTION = typer.Option(
    Path("."),
    "--project-root",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Project root that contains docs/ and site/templates/ for copy linting.",
)

INGESTION_STATUS_OPTION = typer.Option(
    "healthy",
    "--ingestion-status",
    help="Procurement ingestion status: healthy, stale, or failed.",
)

REAL_SEED_SOURCE_DIR_OPTION = typer.Option(
    Path("data_sources") / "public_seed_sources",
    "--source-dir",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Directory containing committed public-source snapshots and the seed manifest.",
)

NOCOPO_FIXTURE_OUTPUT_OPTION = typer.Option(
    Path("tests") / "fixtures" / "nocopo" / "sample.json",
    "--nocopo-fixture-out",
    file_okay=True,
    dir_okay=False,
    resolve_path=True,
    help="Path for writing the deterministic OCDS fixture aligned to the real seed set.",
)

MANIFEST_PATH_OPTION = typer.Option(
    Path("public") / "api" / "v1" / "manifests" / "latest.json",
    "--manifest",
    file_okay=True,
    dir_okay=False,
    readable=True,
    resolve_path=True,
    help="Path to a generated release manifest JSON file.",
)

MANIFEST_ARTIFACT_ROOT_OPTION = typer.Option(
    None,
    "--artifact-root",
    file_okay=False,
    dir_okay=True,
    readable=True,
    resolve_path=True,
    help="Optional artifact root to verify against instead of inferring from the manifest path.",
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


@app.command("generate-real-seed")
def generate_real_public_seed(
    source_dir: Path = REAL_SEED_SOURCE_DIR_OPTION,
    registry_dir: Path = REGISTRY_DIR_OPTION,
    nocopo_fixture_out: Path = NOCOPO_FIXTURE_OUTPUT_OPTION,
) -> None:
    """Generate deterministic real public-source registry seeds."""
    try:
        written = generate_real_seed(
            source_dir=source_dir,
            registry_dir=registry_dir,
            nocopo_fixture_out=nocopo_fixture_out,
        )
    except RealSeedError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(
        "real public-source seed generated: "
        f"{registry_dir} ({written} artifacts written)"
    )


@app.command("validate-seed-sources")
def validate_real_seed_sources(
    source_dir: Path = REAL_SEED_SOURCE_DIR_OPTION,
) -> None:
    """Validate committed public-source snapshots and seed manifest provenance."""
    try:
        result = validate_seed_sources(source_dir)
    except RealSeedError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(
        "seed sources valid: "
        f"{source_dir} "
        f"({result.source_count} sources, "
        f"{result.business_count} businesses, "
        f"{result.evidence_reference_count} evidence refs)"
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


@app.command("ingest-nocopo")
def ingest_nocopo(
    input_path: Path = INGEST_NOCOPO_INPUT_PATH_OPTION,
    registry_dir: Path = SCORE_REGISTRY_OPTION,
    out_dir: Path = INGEST_NOCOPO_OUTPUT_DIR_OPTION,
) -> None:
    """Ingest a local NOCOPO/OCDS fixture into derived supplier metrics."""
    try:
        written = ingest_nocopo_fixture(
            input_path=input_path,
            registry_dir=registry_dir,
            out_dir=out_dir,
        )
    except (IngestionError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"derived NOCOPO records written: {out_dir} ({written} files)")


@app.command("report-ingestion-quality")
def report_ingestion_quality(
    input_path: Path = INGEST_NOCOPO_INPUT_PATH_OPTION,
    derived_dir: Path = DERIVED_NOCOPO_DIR_OPTION,
    out_dir: Path = DERIVED_REPORTS_DIR_OPTION,
    ingestion_status: str = INGESTION_STATUS_OPTION,
    max_age_days: int = MAX_AGE_DAYS_OPTION,
) -> None:
    """Build a deterministic procurement ingestion quality report."""
    try:
        report = build_nocopo_quality_report(
            input_path=input_path,
            derived_dir=derived_dir,
            out_dir=out_dir,
            ingestion_status=ingestion_status,
            max_age_days=max_age_days,
        )
    except (IngestionQualityError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(
        "ingestion quality report written: "
        f"{out_dir} (stale={report.stale}, anomalies={report.anomaly_count})"
    )


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
    ops_dir: Path = OPS_DIR_OPTION,
    ingestion_status: str = INGESTION_STATUS_OPTION,
) -> None:
    """Build static public API artifacts from scored registry inputs."""
    try:
        written = build_public_api(
            registry_dir=registry_dir,
            score_dir=score_dir,
            out_dir=out_dir,
            derived_dir=derived_dir,
            ops_dir=ops_dir,
            ingestion_status=ingestion_status,
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


@app.command("package-cloudflare-pages")
def package_pages_artifact(
    site_dir: Path = PAGES_PACKAGE_SITE_DIR_OPTION,
    api_dir: Path = PAGES_PACKAGE_API_DIR_OPTION,
    out_dir: Path = PAGES_PACKAGE_OUT_DIR_OPTION,
) -> None:
    """Package the public site and API into one Cloudflare Pages deploy directory."""
    try:
        result = package_cloudflare_pages(
            site_dir=site_dir,
            api_dir=api_dir,
            out_dir=out_dir,
        )
    except CloudflarePagesPackageError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(
        "cloudflare pages package written: "
        f"{result.output_dir} ({result.total_file_count} files)"
    )


@app.command("verify-manifest")
def verify_manifest(
    manifest_path: Path = MANIFEST_PATH_OPTION,
    artifact_root: Path | None = MANIFEST_ARTIFACT_ROOT_OPTION,
) -> None:
    """Verify a generated release manifest against artifact bytes on disk."""
    try:
        result = verify_release_manifest(
            manifest_path=manifest_path,
            artifact_root=artifact_root,
        )
    except ManifestVerificationError as error:
        for issue in error.issues:
            typer.echo(issue)
        raise typer.Exit(code=1) from error

    typer.echo(
        "manifest valid: "
        f"{result.manifest_path} ({result.verified_count} artifacts checked)"
    )


@app.command("lint-copy")
def lint_copy(
    project_root: Path = PROJECT_ROOT_OPTION,
) -> None:
    """Lint public-facing docs and templates for unsafe copy."""
    try:
        linted_paths = lint_project_copy(project_root)
    except CopyLintError as error:
        for issue in error.issues:
            typer.echo(issue.render())
        raise typer.Exit(code=1) from error

    typer.echo(f"copy valid: {project_root} ({len(linted_paths)} files checked)")


@app.command("scan-repo-safety")
def scan_repo(
    project_root: Path = PROJECT_ROOT_OPTION,
) -> None:
    """Scan the repository for obvious PII and forbidden public upload types."""
    try:
        scanned_files = scan_repo_safety(project_root)
    except RepoSafetyError as error:
        for issue in error.issues:
            typer.echo(issue.render())
        raise typer.Exit(code=1) from error

    typer.echo(f"repo safety valid: {project_root} ({scanned_files} files checked)")


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
