from __future__ import annotations

import json
import shutil
from pathlib import Path

from btr_ng.policy.config import load_ops_config
from btr_ng.safety.controller import build_safety_report, load_runtime_safety_inputs
from btr_ng.safety.models import QueueSnapshot, RuntimeSafetyInputs
from btr_ng.safety.queue_status import build_queue_status_artifact, evaluate_queue_mode

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
OPS_DIR = PROJECT_ROOT / "ops"
MAINTENANCE_MESSAGE = (
    "Backlog is above maintenance threshold. Scoring may be suppressed under load."
)


def test_evaluate_queue_mode_applies_thresholds() -> None:
    policy = load_ops_config(OPS_DIR).safety_policy

    assert (
        evaluate_queue_mode(
            QueueSnapshot(claims=0, corrections=0, disputes=1, verifications=0),
            backlog_warning_threshold=policy.backlog_warning_threshold,
            maintenance_mode_threshold=policy.maintenance_mode_threshold,
        )
        == "normal"
    )
    assert (
        evaluate_queue_mode(
            QueueSnapshot(claims=5, corrections=3, disputes=2, verifications=0),
            backlog_warning_threshold=policy.backlog_warning_threshold,
            maintenance_mode_threshold=policy.maintenance_mode_threshold,
        )
        == "degraded"
    )
    assert (
        evaluate_queue_mode(
            QueueSnapshot(claims=10, corrections=8, disputes=7, verifications=0),
            backlog_warning_threshold=policy.backlog_warning_threshold,
            maintenance_mode_threshold=policy.maintenance_mode_threshold,
        )
        == "maintenance"
    )


def test_queue_status_artifact_is_deterministic_and_schema_safe() -> None:
    report = build_safety_report(
        RuntimeSafetyInputs(
            ops_config=load_ops_config(OPS_DIR),
            queue=QueueSnapshot(claims=0, corrections=0, disputes=1, verifications=0),
            active_disputes=("BTR-BLUESKY-001",),
            active_dispute_updates={"BTR-BLUESKY-001": "2026-04-07T18:00:00Z"},
            ingestion_status="healthy",
        )
    )

    artifact = build_queue_status_artifact(
        registry_dir=REGISTRY_DIR,
        generated_at="2026-04-07T18:00:00Z",
        safety_report=report,
    )

    assert artifact.to_dict() == {
        "generated_at": "2026-04-07T18:00:00Z",
        "message": "Queue is within normal operating thresholds.",
        "mode": "normal",
        "oldest_open_age_days": 1,
        "open_counts": {
            "claims": 0,
            "corrections": 0,
            "disputes": 1,
            "verifications": 0,
        },
        "stale": False,
    }


def test_load_runtime_safety_inputs_and_queue_status_reflect_maintenance_threshold(
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
        duplicated["case_id"] = f"CASE-BLUESKY-{index:03d}"
        duplicated["btr_id"] = "BTR-BLUESKY-001" if index % 2 == 0 else "BTR-ACME-001"
        (dispute_dir / f"case-extra-{index:03d}.json").write_text(
            json.dumps(duplicated, indent=2) + "\n",
            encoding="utf-8",
        )

    runtime_inputs = load_runtime_safety_inputs(
        registry_dir=registry_copy,
        ops_dir=OPS_DIR,
        ingestion_status="healthy",
    )
    report = build_safety_report(runtime_inputs)
    artifact = build_queue_status_artifact(
        registry_dir=registry_copy,
        generated_at="2026-04-07T18:00:00Z",
        safety_report=report,
    )

    assert report.system_mode == "MAINTENANCE"
    assert artifact.mode == "maintenance"
    assert artifact.message == MAINTENANCE_MESSAGE
