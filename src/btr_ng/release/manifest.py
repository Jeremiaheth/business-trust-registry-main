"""Release manifest generation for published API artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path


class ReleaseManifestError(ValueError):
    """Raised when a release manifest cannot be generated safely."""


def build_release_manifest(
    artifact_root: Path,
    artifact_paths: Sequence[Path],
    generated_at: str,
    artifact_types: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Build a deterministic release manifest for files under a single artifact root."""
    resolved_root = artifact_root.resolve()
    type_map = dict(artifact_types or {})
    artifacts: list[dict[str, object]] = []
    seen_paths: set[str] = set()

    for artifact_path in sorted((path.resolve() for path in artifact_paths), key=_sort_key):
        if not artifact_path.exists():
            raise ReleaseManifestError(f"artifact does not exist: {artifact_path}")
        if not artifact_path.is_file():
            raise ReleaseManifestError(f"artifact path must be a file: {artifact_path}")

        try:
            relative_path = artifact_path.relative_to(resolved_root).as_posix()
        except ValueError as error:
            raise ReleaseManifestError(
                f"artifact is outside the artifact root: {artifact_path}"
            ) from error

        if relative_path in seen_paths:
            raise ReleaseManifestError(f"duplicate artifact entry: {relative_path}")
        seen_paths.add(relative_path)

        artifact = _artifact_metadata(artifact_path, relative_path)
        artifact_type = type_map.get(relative_path)
        if artifact_type is not None:
            artifact["type"] = artifact_type
        artifacts.append(artifact)

    return {
        "generated_at": generated_at,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def write_release_manifest(
    artifact_root: Path,
    artifact_paths: Sequence[Path],
    manifest_path: Path,
    generated_at: str,
    artifact_types: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Write a deterministic release manifest to disk."""
    document = build_release_manifest(
        artifact_root=artifact_root,
        artifact_paths=artifact_paths,
        generated_at=generated_at,
        artifact_types=artifact_types,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return document


def _artifact_metadata(artifact_path: Path, relative_path: str) -> dict[str, object]:
    content = artifact_path.read_bytes()
    return {
        "path": relative_path,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _sort_key(path: Path) -> str:
    return path.as_posix()
