from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.publishing.api_builder import build_public_api
from btr_ng.safety.controller import build_safety_report, load_runtime_safety_inputs
from btr_ng.scoring.engine import score_registry_to_directory
from btr_ng.site_builder.builder import SiteBuildError, build_site

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
OPS_DIR = PROJECT_ROOT / "ops"
SCORING_CONFIG_PATH = PROJECT_ROOT / "spec" / "scoring.toml"
SITE_TEMPLATE_DIR = PROJECT_ROOT / "site" / "templates"
SITE_STATIC_DIR = PROJECT_ROOT / "site" / "static"
MAINTENANCE_MESSAGE = (
    "Backlog is above maintenance threshold. Scoring may be suppressed under load."
)
runner = CliRunner()


def test_build_site_cli_renders_static_html_from_api_artifacts(tmp_path: Path) -> None:
    score_dir = tmp_path / "scores"
    derived_dir = tmp_path / "derived"
    api_dir = tmp_path / "public" / "api" / "v1"
    site_dir = tmp_path / "site" / "dist"
    score_registry_to_directory(
        registry_dir=REGISTRY_DIR,
        config_path=SCORING_CONFIG_PATH,
        out_dir=score_dir,
    )
    build_public_api(
        registry_dir=REGISTRY_DIR,
        score_dir=score_dir,
        out_dir=api_dir,
        derived_dir=derived_dir,
    )

    result = runner.invoke(
        app,
        [
            "build-site",
            "--api",
            str(api_dir),
            "--out",
            str(site_dir),
            "--templates",
            str(SITE_TEMPLATE_DIR),
            "--static-dir",
            str(SITE_STATIC_DIR),
        ],
    )

    assert result.exit_code == 0
    assert "site written" in result.stdout
    assert (site_dir / "index.html").exists()
    assert (site_dir / "queue-status" / "index.html").exists()
    assert (site_dir / "search" / "index.html").exists()
    assert (site_dir / "businesses" / "BTR-BLUESKY-001" / "index.html").exists()
    assert (site_dir / "404.html").exists()

    home_html = (site_dir / "index.html").read_text(encoding="utf-8")
    assert "Public evidence dossier and verification layer" in home_html
    assert "businesses/BTR-ACME-001/" in home_html

    search_html = (site_dir / "search" / "index.html").read_text(encoding="utf-8")
    assert 'data-search-url="../api/v1/search.json"' in search_html
    assert "Search by business name, ID, tag, or identifier" in search_html

    queue_html = (site_dir / "queue-status" / "index.html").read_text(encoding="utf-8")
    assert "Queue status" in queue_html
    assert "Scoring may be suppressed under load." in queue_html

    blue_sky_html = (
        site_dir / "businesses" / "BTR-BLUESKY-001" / "index.html"
    ).read_text(encoding="utf-8")
    assert "Published profile" in blue_sky_html
    assert "Based on available verified evidence." in blue_sky_html
    assert "Last verification update:" in blue_sky_html
    assert "Open source reference" in blue_sky_html


def test_build_site_fails_loudly_when_index_artifact_is_missing(tmp_path: Path) -> None:
    api_dir = tmp_path / "public" / "api" / "v1"
    api_dir.mkdir(parents=True)
    (api_dir / "search.json").write_text('{"entries": []}\n', encoding="utf-8")
    (api_dir / "businesses").mkdir()

    try:
        build_site(
            api_dir=api_dir,
            out_dir=tmp_path / "site" / "dist",
            template_dir=SITE_TEMPLATE_DIR,
            static_dir=SITE_STATIC_DIR,
        )
    except SiteBuildError as error:
        assert "missing required API artifact" in str(error)
        assert "index.json" in str(error)
    else:
        raise AssertionError("expected the site builder to reject incomplete API artifacts")


def test_build_site_renders_maintenance_queue_banner_when_backlog_crosses_threshold(
    tmp_path: Path,
) -> None:
    registry_copy = tmp_path / "registry"
    shutil.copytree(REGISTRY_DIR, registry_copy)
    dispute_dir = registry_copy / "disputes"
    template = json.loads(
        (dispute_dir / "case-bluesky-metadata-review.json").read_text(encoding="utf-8")
    )
    for index in range(2, 26):
        duplicated = dict(template)
        duplicated["case_id"] = f"CASE-MAINT-{index:03d}"
        duplicated["btr_id"] = "BTR-BLUESKY-001" if index % 2 == 0 else "BTR-ACME-001"
        (dispute_dir / f"case-maint-{index:03d}.json").write_text(
            json.dumps(duplicated, indent=2) + "\n",
            encoding="utf-8",
        )

    score_dir = tmp_path / "scores"
    derived_dir = tmp_path / "derived"
    api_dir = tmp_path / "public" / "api" / "v1"
    site_dir = tmp_path / "site" / "dist"
    safety_report = build_safety_report(
        load_runtime_safety_inputs(
            registry_dir=registry_copy,
            ops_dir=OPS_DIR,
            ingestion_status="healthy",
        )
    )
    score_registry_to_directory(
        registry_dir=registry_copy,
        config_path=SCORING_CONFIG_PATH,
        out_dir=score_dir,
        safety_report=safety_report,
    )
    build_public_api(
        registry_dir=registry_copy,
        score_dir=score_dir,
        out_dir=api_dir,
        derived_dir=derived_dir,
        ops_dir=OPS_DIR,
        ingestion_status="healthy",
    )
    build_site(
        api_dir=api_dir,
        out_dir=site_dir,
        template_dir=SITE_TEMPLATE_DIR,
        static_dir=SITE_STATIC_DIR,
    )

    home_html = (site_dir / "index.html").read_text(encoding="utf-8")
    queue_html = (site_dir / "queue-status" / "index.html").read_text(encoding="utf-8")
    profile_html = (
        site_dir / "businesses" / "BTR-ACME-001" / "index.html"
    ).read_text(encoding="utf-8")

    assert MAINTENANCE_MESSAGE in home_html
    assert MAINTENANCE_MESSAGE in queue_html
    assert "Scoring may be suppressed under load." in profile_html
