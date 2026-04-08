from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from btr_ng.policy.config import load_ops_config
from btr_ng.registry.disputes import (
    active_dispute_business_ids,
    load_dispute_records,
)
from btr_ng.safety.controller import build_safety_report, load_runtime_safety_inputs
from btr_ng.safety.models import QueueSnapshot, RuntimeSafetyInputs
from btr_ng.schema import SchemaValidationError, validate_document
from btr_ng.scoring.engine import score_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
OPS_DIR = PROJECT_ROOT / "ops"
SCORING_CONFIG_PATH = PROJECT_ROOT / "spec" / "scoring.toml"


def test_dispute_schema_rejects_raw_evidence_like_fields() -> None:
    with pytest.raises(SchemaValidationError) as error:
        validate_document(
            "dispute-record",
            {
                "case_id": "CASE-ACME-001",
                "btr_id": "BTR-ACME-001",
                "review_type": "fact_correction",
                "state": "under_review",
                "redacted_summary": "Public fact-correction review.",
                "evidence_pack_refs": ["HASH-ACME-001"],
                "opened_at": "2026-04-07T10:00:00Z",
                "updated_at": "2026-04-07T11:00:00Z",
                "raw_evidence_blob": "forbidden",
            },
        )

    assert any("$" in issue for issue in error.value.issues)


def test_active_dispute_forces_under_review_and_uses_latest_review_timestamp() -> None:
    disputes = load_dispute_records(REGISTRY_DIR / "disputes")
    latest_review_timestamp = "2026-04-09T09:30:00Z"
    report = build_safety_report(
        RuntimeSafetyInputs(
            ops_config=load_ops_config(OPS_DIR),
            queue=QueueSnapshot(claims=0, corrections=0, disputes=1, verifications=0),
            active_disputes=active_dispute_business_ids(disputes),
            active_dispute_updates={"BTR-BLUESKY-001": latest_review_timestamp},
            ingestion_status="healthy",
        )
    )

    snapshots = score_registry(REGISTRY_DIR, SCORING_CONFIG_PATH, safety_report=report)
    blue_sky = next(snapshot for snapshot in snapshots if snapshot.btr_id == "BTR-BLUESKY-001")

    assert blue_sky.display_state == "under_review"
    assert blue_sky.status == "under_review"
    assert blue_sky.verification_timestamp == latest_review_timestamp


def test_resolved_dispute_restores_normal_score_path(tmp_path: Path) -> None:
    registry_copy = tmp_path / "registry"
    shutil.copytree(REGISTRY_DIR, registry_copy)
    dispute_path = registry_copy / "disputes" / "case-bluesky-metadata-review.json"
    dispute = json.loads(dispute_path.read_text(encoding="utf-8"))
    dispute["state"] = "resolved"
    dispute["resolution_note"] = "Metadata correction completed."
    dispute["updated_at"] = "2026-04-08T09:00:00Z"
    dispute_path.write_text(json.dumps(dispute, indent=2) + "\n", encoding="utf-8")

    runtime_inputs = load_runtime_safety_inputs(
        registry_dir=registry_copy,
        ops_dir=OPS_DIR,
        ingestion_status="healthy",
    )
    report = build_safety_report(runtime_inputs)
    snapshots = score_registry(registry_copy, SCORING_CONFIG_PATH, safety_report=report)
    blue_sky = next(snapshot for snapshot in snapshots if snapshot.btr_id == "BTR-BLUESKY-001")

    assert report.active_disputes == ()
    assert blue_sky.display_state == "normal"
    assert blue_sky.status == "published"
