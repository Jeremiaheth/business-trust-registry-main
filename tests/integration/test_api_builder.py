from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.publishing.api_builder import ApiBuildError, build_public_api
from btr_ng.safety.controller import build_safety_report, load_runtime_safety_inputs
from btr_ng.scoring.engine import score_registry_to_directory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
OPS_DIR = PROJECT_ROOT / "ops"
SCORING_CONFIG_PATH = PROJECT_ROOT / "spec" / "scoring.toml"
runner = CliRunner()


def test_build_api_cli_writes_static_public_artifacts(tmp_path: Path) -> None:
    score_dir = tmp_path / "scores"
    derived_dir = tmp_path / "derived"
    out_dir = tmp_path / "public" / "api" / "v1"
    runtime_inputs = load_runtime_safety_inputs(
        registry_dir=REGISTRY_DIR,
        ops_dir=OPS_DIR,
        ingestion_status="healthy",
    )
    safety_report = build_safety_report(runtime_inputs)
    score_registry_to_directory(
        registry_dir=REGISTRY_DIR,
        config_path=SCORING_CONFIG_PATH,
        out_dir=score_dir,
        safety_report=safety_report,
    )

    result = runner.invoke(
        app,
        [
            "build-api",
            "--registry",
            str(REGISTRY_DIR),
            "--scores",
            str(score_dir),
            "--derived",
            str(derived_dir),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert "public API written" in result.stdout
    assert (out_dir / "index.json").exists()
    assert (out_dir / "queue_status.json").exists()
    assert (out_dir / "search.json").exists()
    assert (out_dir / "manifests" / "latest.json").exists()
    assert (out_dir / "businesses" / "BTR-ACME-001.json").exists()
    assert (out_dir / "businesses" / "BTR-BLUESKY-001.json").exists()
    assert (out_dir / "businesses" / "BTR-LAGOON-001.json").exists()

    index_document = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
    assert index_document["counts"] == {"businesses": 3, "evidence": 5, "open_disputes": 1}
    assert [item["btr_id"] for item in index_document["items"]] == [
        "BTR-ACME-001",
        "BTR-BLUESKY-001",
        "BTR-LAGOON-001",
    ]

    blue_sky_document = json.loads(
        (out_dir / "businesses" / "BTR-BLUESKY-001.json").read_text(encoding="utf-8")
    )
    assert blue_sky_document["score"]["display_state"] == "under_review"
    assert len(blue_sky_document["evidence"]) == 1
    assert len(blue_sky_document["disputes"]) == 1
    assert blue_sky_document["derived_records"] == []

    search_document = json.loads((out_dir / "search.json").read_text(encoding="utf-8"))
    blue_sky_entry = next(
        entry for entry in search_document["entries"] if entry["btr_id"] == "BTR-BLUESKY-001"
    )
    assert blue_sky_entry["display_state"] == "under_review"
    assert "directory-listing" in blue_sky_entry["tags"]
    assert "blue sky catering cooperative" in blue_sky_entry["terms"]

    queue_status_document = json.loads(
        (out_dir / "queue_status.json").read_text(encoding="utf-8")
    )
    assert queue_status_document["mode"] == "normal"
    assert queue_status_document["stale"] is False
    assert queue_status_document["open_counts"]["disputes"] == 1

    manifest_document = json.loads(
        (out_dir / "manifests" / "latest.json").read_text(encoding="utf-8")
    )
    assert manifest_document["artifact_count"] == 6
    assert [artifact["path"] for artifact in manifest_document["artifacts"]] == [
        "businesses/BTR-ACME-001.json",
        "businesses/BTR-BLUESKY-001.json",
        "businesses/BTR-LAGOON-001.json",
        "index.json",
        "queue_status.json",
        "search.json",
    ]


def test_build_api_fails_loudly_when_a_business_score_is_missing(tmp_path: Path) -> None:
    score_dir = tmp_path / "scores"
    derived_dir = tmp_path / "derived"
    out_dir = tmp_path / "public" / "api" / "v1"
    runtime_inputs = load_runtime_safety_inputs(
        registry_dir=REGISTRY_DIR,
        ops_dir=OPS_DIR,
        ingestion_status="healthy",
    )
    safety_report = build_safety_report(runtime_inputs)
    score_registry_to_directory(
        registry_dir=REGISTRY_DIR,
        config_path=SCORING_CONFIG_PATH,
        out_dir=score_dir,
        safety_report=safety_report,
    )
    (score_dir / "BTR-LAGOON-001.json").unlink()

    try:
        build_public_api(
            registry_dir=REGISTRY_DIR,
            score_dir=score_dir,
            out_dir=out_dir,
            derived_dir=derived_dir,
        )
    except ApiBuildError as error:
        assert "missing trust score snapshots for: BTR-LAGOON-001" in str(error)
    else:
        raise AssertionError("expected the API builder to reject incomplete score inputs")
