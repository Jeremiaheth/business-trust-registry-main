from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.publishing.api_builder import ApiBuildError, build_public_api
from btr_ng.release import verify_release_manifest
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
    assert (out_dir / "reports" / "BTR-ACME-001.json").exists()
    assert (out_dir / "reports" / "BTR-BLUESKY-001.json").exists()
    assert (out_dir / "businesses" / "BTR-ACME-001.json").exists()
    assert (out_dir / "businesses" / "BTR-BLUESKY-001.json").exists()
    assert (out_dir / "businesses" / "BTR-LAGOON-001.json").exists()
    assert (out_dir / "businesses" / "BTR-MESA-001.json").exists()

    index_document = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
    assert index_document["counts"] == {"businesses": 12, "evidence": 26, "open_disputes": 2}
    assert [item["btr_id"] for item in index_document["items"]] == [
        "BTR-ACME-001",
        "BTR-BLUESKY-001",
        "BTR-CEDAR-001",
        "BTR-DELTA-001",
        "BTR-EMBER-001",
        "BTR-FALCON-001",
        "BTR-GRANITE-001",
        "BTR-HARBOR-001",
        "BTR-IVORY-001",
        "BTR-JETTY-001",
        "BTR-LAGOON-001",
        "BTR-MESA-001",
    ]
    assert index_document["filters"]["verified_status"]["enabled"] is True
    assert index_document["filters"]["sector"]["enabled"] is False
    assert index_document["filters"]["location"]["enabled"] is False

    blue_sky_document = json.loads(
        (out_dir / "businesses" / "BTR-BLUESKY-001.json").read_text(encoding="utf-8")
    )
    assert blue_sky_document["score"]["display_state"] == "under_review"
    assert len(blue_sky_document["evidence"]) == 1
    assert len(blue_sky_document["disputes"]) == 1
    assert blue_sky_document["derived_records"] == []
    assert blue_sky_document["presentation"]["trust_status_label"] == "Under review"
    assert (
        blue_sky_document["presentation"]["verification_panels"]["cac"]["availability"]
        == "unavailable_beta"
    )
    assert (
        blue_sky_document["presentation"]["verification_panels"]["psc"]["availability"]
        == "unavailable_beta"
    )
    assert blue_sky_document["presentation"]["report"]["availability"] == "html_only"
    assert blue_sky_document["presentation"]["report"]["route"] == "/reports/BTR-BLUESKY-001"

    search_document = json.loads((out_dir / "search.json").read_text(encoding="utf-8"))
    assert search_document["filters"]["confidence_level"]["enabled"] is True
    assert search_document["filters"]["sector"]["enabled"] is False
    blue_sky_entry = next(
        entry for entry in search_document["entries"] if entry["btr_id"] == "BTR-BLUESKY-001"
    )
    assert blue_sky_entry["display_state"] == "under_review"
    assert blue_sky_entry["confidence_band"] in {"limited", "moderate", "strong"}
    assert "federal-nocopo" in blue_sky_entry["tags"]
    assert "single-public-procurement-reference" in blue_sky_entry["tags"]
    assert "laurmann & company ltd" in blue_sky_entry["terms"]
    assert blue_sky_entry["filters"]["open_review"] == "under_review"
    jetty_entry = next(
        entry for entry in search_document["entries"] if entry["btr_id"] == "BTR-JETTY-001"
    )
    assert jetty_entry["display_state"] == "under_review"
    mesa_entry = next(
        entry for entry in search_document["entries"] if entry["btr_id"] == "BTR-MESA-001"
    )
    assert mesa_entry["display_state"] == "insufficient_evidence"
    assert "aging-public-procurement-reference" in mesa_entry["tags"]

    queue_status_document = json.loads(
        (out_dir / "queue_status.json").read_text(encoding="utf-8")
    )
    assert queue_status_document["mode"] == "normal"
    assert queue_status_document["stale"] is False
    assert queue_status_document["open_counts"]["disputes"] == 2

    report_document = json.loads(
        (out_dir / "reports" / "BTR-BLUESKY-001.json").read_text(encoding="utf-8")
    )
    assert report_document["title"] == "Laurmann & Company trust report"
    assert report_document["scorecard"]["display_state"] == "under_review"
    assert report_document["verification_panels"]["cac"]["availability"] == "unavailable_beta"
    assert any(item["type"] == "fact_correction" for item in report_document["timeline"])

    manifest_document = json.loads(
        (out_dir / "manifests" / "latest.json").read_text(encoding="utf-8")
    )
    assert manifest_document["artifact_count"] == 27
    assert manifest_document["artifacts"][0]["path"] == "businesses/BTR-ACME-001.json"
    assert manifest_document["artifacts"][12]["path"] == "index.json"
    assert manifest_document["artifacts"][13]["path"] == "queue_status.json"
    assert manifest_document["artifacts"][14]["path"] == "reports/BTR-ACME-001.json"
    assert manifest_document["artifacts"][-1]["path"] == "search.json"

    verification = verify_release_manifest(out_dir / "manifests" / "latest.json")
    assert verification.verified_count == 27


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
