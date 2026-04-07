from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.publishing.api_builder import build_public_api
from btr_ng.scoring.engine import score_registry_to_directory
from btr_ng.site_builder.builder import SiteBuildError, build_site

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
SCORING_CONFIG_PATH = PROJECT_ROOT / "spec" / "scoring.toml"
DERIVED_DIR = PROJECT_ROOT / "derived"
SITE_TEMPLATE_DIR = PROJECT_ROOT / "site" / "templates"
SITE_STATIC_DIR = PROJECT_ROOT / "site" / "static"
runner = CliRunner()


def test_build_site_cli_renders_static_html_from_api_artifacts(tmp_path: Path) -> None:
    score_dir = tmp_path / "scores"
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
        derived_dir=DERIVED_DIR,
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
    assert (site_dir / "search" / "index.html").exists()
    assert (site_dir / "businesses" / "BTR-BLUESKY-001" / "index.html").exists()
    assert (site_dir / "404.html").exists()

    home_html = (site_dir / "index.html").read_text(encoding="utf-8")
    assert "Public evidence dossier and verification layer" in home_html
    assert "businesses/BTR-ACME-001/" in home_html

    search_html = (site_dir / "search" / "index.html").read_text(encoding="utf-8")
    assert 'data-search-url="../api/v1/search.json"' in search_html
    assert "Search by business name, ID, tag, or identifier" in search_html

    blue_sky_html = (
        site_dir / "businesses" / "BTR-BLUESKY-001" / "index.html"
    ).read_text(encoding="utf-8")
    assert "Insufficient evidence" in blue_sky_html
    assert "Insufficient verified evidence is available for a stable public score." in blue_sky_html
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
