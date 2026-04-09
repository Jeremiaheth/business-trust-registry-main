"""Package deterministic Cloudflare deploy artifacts."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


class CloudflarePagesPackageError(ValueError):
    """Raised when Cloudflare deploy artifacts cannot be packaged safely."""


@dataclass(frozen=True)
class CloudflarePagesPackageResult:
    """Summary of a packaged Cloudflare Pages artifact bundle."""

    output_dir: Path
    site_file_count: int
    api_file_count: int

    @property
    def total_file_count(self) -> int:
        """Return the total number of packaged files."""
        return self.site_file_count + self.api_file_count


def package_cloudflare_pages(
    *,
    site_dir: Path,
    api_dir: Path,
    out_dir: Path,
) -> CloudflarePagesPackageResult:
    """Build a Pages-ready artifact directory from static site and API outputs."""
    _require_directory(site_dir, "site build directory")
    _require_directory(api_dir, "public API directory")
    _require_file(site_dir / "index.html", "site root index")
    _require_file(api_dir / "index.json", "public API index")
    _require_file(api_dir / "manifests" / "latest.json", "release manifest")

    if out_dir.exists():
        if not out_dir.is_dir():
            raise CloudflarePagesPackageError(
                f"Cloudflare package output path must be a directory: {out_dir}"
            )
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    site_file_count = _copy_tree_contents(site_dir, out_dir)
    api_target_dir = out_dir / "api" / "v1"
    api_file_count = _copy_tree_contents(api_dir, api_target_dir)

    _require_file(out_dir / "index.html", "packaged site root index")
    _require_file(api_target_dir / "index.json", "packaged API index")
    _require_file(api_target_dir / "manifests" / "latest.json", "packaged release manifest")

    return CloudflarePagesPackageResult(
        output_dir=out_dir.resolve(),
        site_file_count=site_file_count,
        api_file_count=api_file_count,
    )


def _copy_tree_contents(source_dir: Path, destination_dir: Path) -> int:
    destination_dir.mkdir(parents=True, exist_ok=True)
    copied_files = 0

    for source_path in sorted(source_dir.iterdir(), key=lambda path: path.name):
        destination_path = destination_dir / source_path.name
        if source_path.is_dir():
            shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
            copied_files += sum(
                1 for nested_path in source_path.rglob("*") if nested_path.is_file()
            )
            continue

        shutil.copy2(source_path, destination_path)
        copied_files += 1

    return copied_files


def _require_directory(path: Path, label: str) -> None:
    if not path.exists():
        raise CloudflarePagesPackageError(f"missing required {label}: {path}")
    if not path.is_dir():
        raise CloudflarePagesPackageError(f"{label} must be a directory: {path}")


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise CloudflarePagesPackageError(f"missing required {label}: {path}")
    if not path.is_file():
        raise CloudflarePagesPackageError(f"{label} must be a file: {path}")
