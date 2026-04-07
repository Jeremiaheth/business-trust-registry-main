from __future__ import annotations

import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.release import (
    ManifestVerificationError,
    build_release_manifest,
    verify_release_manifest,
)
from btr_ng.release.manifest import write_release_manifest

runner = CliRunner()


def test_build_release_manifest_records_relative_paths_and_checksums(tmp_path: Path) -> None:
    artifact_root = tmp_path / "public" / "api" / "v1"
    business_path = artifact_root / "businesses" / "BTR-ACME-001.json"
    index_path = artifact_root / "index.json"
    business_path.parent.mkdir(parents=True, exist_ok=True)
    business_path.write_text('{"btr_id": "BTR-ACME-001"}\n', encoding="utf-8")
    index_path.write_text('{"items": []}\n', encoding="utf-8")

    document = build_release_manifest(
        artifact_root=artifact_root,
        artifact_paths=[business_path, index_path],
        generated_at="2026-04-07T18:00:00Z",
        artifact_types={
            "businesses/BTR-ACME-001.json": "business",
            "index.json": "index",
        },
    )

    assert document["artifact_count"] == 2
    assert document["artifacts"] == [
        {
            "bytes": len(business_path.read_bytes()),
            "path": "businesses/BTR-ACME-001.json",
            "sha256": hashlib.sha256(business_path.read_bytes()).hexdigest(),
            "type": "business",
        },
        {
            "bytes": len(index_path.read_bytes()),
            "path": "index.json",
            "sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
            "type": "index",
        },
    ]


def test_verify_release_manifest_cli_succeeds_for_written_manifest(tmp_path: Path) -> None:
    artifact_root = tmp_path / "public" / "api" / "v1"
    artifact_path = artifact_root / "index.json"
    manifest_path = artifact_root / "manifests" / "latest.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text('{"items": []}\n', encoding="utf-8")

    write_release_manifest(
        artifact_root=artifact_root,
        artifact_paths=[artifact_path],
        manifest_path=manifest_path,
        generated_at="2026-04-07T18:00:00Z",
        artifact_types={"index.json": "index"},
    )

    result = runner.invoke(app, ["verify-manifest", "--manifest", str(manifest_path)])

    assert result.exit_code == 0
    assert "manifest valid:" in result.stdout

    verification = verify_release_manifest(manifest_path)
    assert verification.artifact_root == artifact_root.resolve()
    assert verification.verified_count == 1


def test_verify_release_manifest_rejects_checksum_mismatch(tmp_path: Path) -> None:
    artifact_root = tmp_path / "public" / "api" / "v1"
    artifact_path = artifact_root / "search.json"
    manifest_path = artifact_root / "manifests" / "latest.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps({"entries": []}) + "\n", encoding="utf-8")

    write_release_manifest(
        artifact_root=artifact_root,
        artifact_paths=[artifact_path],
        manifest_path=manifest_path,
        generated_at="2026-04-07T18:00:00Z",
        artifact_types={"search.json": "search"},
    )

    artifact_path.write_text(json.dumps({"entries": ["tampered"]}) + "\n", encoding="utf-8")

    try:
        verify_release_manifest(manifest_path)
    except ManifestVerificationError as error:
        assert len(error.issues) == 2
        assert "search.json: byte count mismatch" in error.issues[0]
        assert "search.json: sha256 mismatch" in error.issues[1]
    else:
        raise AssertionError("expected checksum verification to fail after tampering")
