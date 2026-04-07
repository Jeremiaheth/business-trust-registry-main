"""Verification helpers for release manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast


class ManifestVerificationError(ValueError):
    """Raised when a release manifest fails verification."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("\n".join(self.issues))


@dataclass(frozen=True, slots=True)
class ManifestVerificationResult:
    """Summary of a successful manifest verification run."""

    manifest_path: Path
    artifact_root: Path
    verified_count: int


def verify_release_manifest(
    manifest_path: Path,
    artifact_root: Path | None = None,
) -> ManifestVerificationResult:
    """Verify that a release manifest matches the current artifact bytes on disk."""
    resolved_manifest = manifest_path.resolve()
    document = _load_manifest_document(resolved_manifest)
    resolved_root = _resolve_artifact_root(resolved_manifest, artifact_root)
    artifacts = _coerce_artifacts(document)

    issues: list[str] = []
    seen_paths: set[str] = set()

    for artifact in artifacts:
        path_value = artifact.get("path")
        sha256_value = artifact.get("sha256")
        bytes_value = artifact.get("bytes")

        if not isinstance(path_value, str) or not _is_safe_relative_path(path_value):
            issues.append(f"manifest contains an invalid artifact path: {path_value!r}")
            continue
        if not isinstance(sha256_value, str) or len(sha256_value) != 64:
            issues.append(f"{path_value}: manifest sha256 must be a 64-character hex string")
            continue
        if not isinstance(bytes_value, int) or bytes_value < 0:
            issues.append(f"{path_value}: manifest bytes must be a non-negative integer")
            continue
        if path_value in seen_paths:
            issues.append(f"manifest contains a duplicate artifact path: {path_value}")
            continue
        seen_paths.add(path_value)

        artifact_path = resolved_root / Path(path_value)
        if not artifact_path.exists():
            issues.append(f"{path_value}: artifact is missing from {resolved_root}")
            continue
        if not artifact_path.is_file():
            issues.append(f"{path_value}: artifact path is not a file")
            continue

        content = artifact_path.read_bytes()
        actual_bytes = len(content)
        if actual_bytes != bytes_value:
            issues.append(f"{path_value}: byte count mismatch ({actual_bytes} != {bytes_value})")

        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != sha256_value:
            issues.append(f"{path_value}: sha256 mismatch ({actual_sha256} != {sha256_value})")

    artifact_count = document.get("artifact_count")
    if not isinstance(artifact_count, int):
        issues.append("manifest artifact_count must be an integer")
    elif artifact_count != len(artifacts):
        issues.append(
            f"manifest artifact_count mismatch ({artifact_count} != {len(artifacts)})"
        )

    if issues:
        raise ManifestVerificationError(issues)

    return ManifestVerificationResult(
        manifest_path=resolved_manifest,
        artifact_root=resolved_root,
        verified_count=len(artifacts),
    )


def _load_manifest_document(manifest_path: Path) -> dict[str, object]:
    if not manifest_path.exists():
        raise ManifestVerificationError([f"manifest does not exist: {manifest_path}"])

    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ManifestVerificationError(
            [f"{manifest_path}: invalid JSON: {error.msg}"]
        ) from error

    if not isinstance(document, dict):
        raise ManifestVerificationError([f"{manifest_path}: expected a top-level JSON object"])
    return cast(dict[str, object], document)


def _coerce_artifacts(document: dict[str, object]) -> list[dict[str, object]]:
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        raise ManifestVerificationError(["manifest artifacts must be a JSON array"])

    result: list[dict[str, object]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ManifestVerificationError(["manifest artifact entries must be JSON objects"])
        result.append(cast(dict[str, object], artifact))
    return result


def _resolve_artifact_root(manifest_path: Path, artifact_root: Path | None) -> Path:
    if artifact_root is not None:
        return artifact_root.resolve()
    if manifest_path.parent.name == "manifests":
        return manifest_path.parent.parent.resolve()
    return manifest_path.parent.resolve()


def _is_safe_relative_path(path_value: str) -> bool:
    relative_path = PurePosixPath(path_value)
    if not path_value or "\\" in path_value or ":" in path_value:
        return False
    if relative_path.is_absolute():
        return False
    return ".." not in relative_path.parts
