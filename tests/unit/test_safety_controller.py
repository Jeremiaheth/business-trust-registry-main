from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.policy.config import load_ops_config
from btr_ng.safety.controller import build_safety_report, load_runtime_safety_inputs
from btr_ng.safety.models import QueueSnapshot, RuntimeSafetyInputs
from btr_ng.scoring.config import load_scoring_config
from btr_ng.scoring.engine import score_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
OPS_DIR = PROJECT_ROOT / "ops"
SCORING_CONFIG_PATH = PROJECT_ROOT / "spec" / "scoring.toml"
runner = CliRunner()


def _base_inputs() -> RuntimeSafetyInputs:
    return RuntimeSafetyInputs(
        ops_config=load_ops_config(OPS_DIR),
        queue=QueueSnapshot(claims=0, corrections=0, disputes=2, verifications=0),
        active_disputes=("BTR-BLUESKY-001", "BTR-JETTY-001"),
        active_dispute_updates={
            "BTR-BLUESKY-001": "2026-04-07T18:00:00Z",
            "BTR-JETTY-001": "2026-04-08T00:00:00Z",
        },
        ingestion_status="healthy",
    )


def test_active_dispute_forces_under_review_profile() -> None:
    report = build_safety_report(_base_inputs())

    decision = report.profile_decision("BTR-BLUESKY-001")

    assert decision.force_under_review is True
    assert decision.suppress_scoring is True
    assert decision.review_timestamp == "2026-04-07T18:00:00Z"


def test_maintenance_threshold_disables_scoring() -> None:
    inputs = replace(
        _base_inputs(),
        queue=QueueSnapshot(claims=10, corrections=8, disputes=7, verifications=1),
    )

    report = build_safety_report(inputs)

    assert report.system_mode == "MAINTENANCE"
    assert report.scoring_enabled is False
    assert any("temporarily paused" in message for message in report.public_banner_messages)


def test_warning_threshold_adds_banner_without_full_maintenance() -> None:
    inputs = replace(
        _base_inputs(),
        queue=QueueSnapshot(claims=5, corrections=3, disputes=2, verifications=0),
    )

    report = build_safety_report(inputs)

    assert report.system_mode == "NORMAL"
    assert any("Backlog is elevated" in message for message in report.public_banner_messages)


def test_privacy_violation_forces_shutdown() -> None:
    inputs = _base_inputs()
    unsafe_ops = replace(
        inputs.ops_config,
        privacy_posture=replace(
            inputs.ops_config.privacy_posture,
            public_repo_accepts_personal_data=True,
        ),
    )

    report = build_safety_report(replace(inputs, ops_config=unsafe_ops))

    assert report.system_mode == "SHUTDOWN"
    assert report.scoring_enabled is False
    assert report.evidence_uploads_enabled is False


def test_ingestion_failure_marks_procurement_signals_stale() -> None:
    report = build_safety_report(replace(_base_inputs(), ingestion_status="failed"))

    assert report.procurement_signals_stale is True
    assert any(
        "Procurement ingestion is currently degraded" in message
        for message in report.public_banner_messages
    )


def test_combined_scenario_keeps_uploads_and_verifier_mode_off() -> None:
    report = build_safety_report(
        replace(
            _base_inputs(),
            queue=QueueSnapshot(claims=2, corrections=1, disputes=1, verifications=0),
            ingestion_status="stale",
        )
    )

    assert report.system_mode == "NORMAL"
    assert report.evidence_uploads_enabled is False
    assert report.verifier_programme_enabled is False
    assert report.procurement_signals_stale is True


def test_score_engine_consumes_maintenance_mode_cleanly() -> None:
    inputs = replace(
        _base_inputs(),
        queue=QueueSnapshot(claims=20, corrections=3, disputes=3, verifications=0),
    )
    report = build_safety_report(inputs)
    config = load_scoring_config(SCORING_CONFIG_PATH)
    snapshots = score_registry(REGISTRY_DIR, SCORING_CONFIG_PATH, safety_report=report)

    acme = next(snapshot for snapshot in snapshots if snapshot.btr_id == "BTR-ACME-001")

    assert report.system_mode == "MAINTENANCE"
    assert acme.status == "suppressed"
    assert len(acme.dimensions) == len(config.dimensions)


def test_safety_report_cli_outputs_json() -> None:
    result = runner.invoke(app, ["safety-report"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["active_disputes"] == ["BTR-BLUESKY-001", "BTR-JETTY-001"]
    assert payload["system_mode"] == "NORMAL"


def test_load_runtime_safety_inputs_reads_registry_and_ops() -> None:
    runtime_inputs = load_runtime_safety_inputs(
        registry_dir=REGISTRY_DIR,
        ops_dir=OPS_DIR,
        ingestion_status="healthy",
    )

    assert runtime_inputs.queue.disputes == 2
    assert runtime_inputs.active_disputes == ("BTR-BLUESKY-001", "BTR-JETTY-001")
