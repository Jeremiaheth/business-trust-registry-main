from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.deploy.cloudflare import CloudflarePagesPackageError, package_cloudflare_pages

runner = CliRunner()


def test_package_cloudflare_pages_merges_site_and_api_outputs(tmp_path: Path) -> None:
    site_dir = tmp_path / "site" / "dist"
    api_dir = tmp_path / "public" / "api" / "v1"
    out_dir = tmp_path / "build" / "cloudflare" / "pages"

    (site_dir / "businesses").mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text("<html>home</html>\n", encoding="utf-8")
    (site_dir / "businesses" / "index.html").write_text("<html>profile</html>\n", encoding="utf-8")

    (api_dir / "manifests").mkdir(parents=True, exist_ok=True)
    (api_dir / "index.json").write_text('{"items": []}\n', encoding="utf-8")
    (api_dir / "manifests" / "latest.json").write_text('{"artifacts": []}\n', encoding="utf-8")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stale.txt").write_text("remove me\n", encoding="utf-8")

    result = package_cloudflare_pages(site_dir=site_dir, api_dir=api_dir, out_dir=out_dir)

    assert result.site_file_count == 2
    assert result.api_file_count == 2
    assert result.total_file_count == 4
    assert (out_dir / "index.html").read_text(encoding="utf-8") == "<html>home</html>\n"
    assert (
        out_dir / "businesses" / "index.html"
    ).read_text(encoding="utf-8") == "<html>profile</html>\n"
    assert (out_dir / "api" / "v1" / "index.json").read_text(encoding="utf-8") == '{"items": []}\n'
    assert (
        out_dir / "api" / "v1" / "manifests" / "latest.json"
    ).read_text(encoding="utf-8") == '{"artifacts": []}\n'
    assert not (out_dir / "stale.txt").exists()


def test_package_cloudflare_pages_requires_release_manifest(tmp_path: Path) -> None:
    site_dir = tmp_path / "site" / "dist"
    api_dir = tmp_path / "public" / "api" / "v1"

    site_dir.mkdir(parents=True)
    api_dir.mkdir(parents=True)
    (site_dir / "index.html").write_text("<html>home</html>\n", encoding="utf-8")
    (api_dir / "index.json").write_text('{"items": []}\n', encoding="utf-8")

    try:
        package_cloudflare_pages(
            site_dir=site_dir,
            api_dir=api_dir,
            out_dir=tmp_path / "build" / "cloudflare" / "pages",
        )
    except CloudflarePagesPackageError as error:
        assert "missing required release manifest" in str(error)
    else:
        raise AssertionError("expected packaging to reject API outputs without a release manifest")


def test_package_cloudflare_pages_cli_writes_merged_directory(tmp_path: Path) -> None:
    site_dir = tmp_path / "site" / "dist"
    api_dir = tmp_path / "public" / "api" / "v1"
    out_dir = tmp_path / "build" / "cloudflare" / "pages"

    (site_dir / "search").mkdir(parents=True, exist_ok=True)
    (site_dir / "index.html").write_text("<html>home</html>\n", encoding="utf-8")
    (site_dir / "search" / "index.html").write_text("<html>search</html>\n", encoding="utf-8")
    (api_dir / "manifests").mkdir(parents=True, exist_ok=True)
    (api_dir / "index.json").write_text('{"items": []}\n', encoding="utf-8")
    (api_dir / "manifests" / "latest.json").write_text('{"artifacts": []}\n', encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "package-cloudflare-pages",
            "--site-dir",
            str(site_dir),
            "--api-dir",
            str(api_dir),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert "cloudflare pages package written:" in result.stdout
    assert (out_dir / "index.html").exists()
    assert (out_dir / "api" / "v1" / "manifests" / "latest.json").exists()
