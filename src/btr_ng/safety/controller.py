"""Deterministic safety controller for BTR-NG."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from btr_ng.policy.config import load_ops_config
from btr_ng.registry.validator import validate_registry_dir
from btr_ng.safety.models import (
    IngestionStatusName,
    QueueSnapshot,
    RuntimeSafetyInputs,
    SafetyReport,
    SystemModeName,
)


def build_safety_report(inputs: RuntimeSafetyInputs) -> SafetyReport:
    """Build a deterministic safety report from runtime inputs."""
    banners: list[str] = []
    queue_total = inputs.queue.total_open
    policy = inputs.ops_config.safety_policy

    system_mode: SystemModeName = "NORMAL"
    scoring_enabled = True

    if inputs.ops_config.privacy_posture.public_repo_accepts_personal_data:
        system_mode = "SHUTDOWN"
        scoring_enabled = False
        banners.append("Public repo privacy posture is unsafe. System is in shutdown mode.")
    elif queue_total >= policy.maintenance_mode_threshold:
        system_mode = "MAINTENANCE"
        scoring_enabled = False
        banners.append("Backlog is above maintenance threshold. Scoring is temporarily paused.")
    elif queue_total >= policy.backlog_warning_threshold:
        banners.append("Backlog is elevated. Reviews may be slower than normal.")

    procurement_signals_stale = inputs.ingestion_status != "healthy"
    if inputs.ingestion_status == "stale":
        banners.append("Procurement-linked signals are stale and may lag recent activity.")
    elif inputs.ingestion_status == "failed":
        banners.append("Procurement ingestion is currently degraded. Related signals may be stale.")

    evidence_uploads_enabled = (
        scoring_enabled
        and inputs.ops_config.policy_gates.enable_evidence_uploads
        and inputs.ops_config.privacy_posture.public_repo_accepts_evidence_uploads
    )

    verifier_programme_enabled = (
        scoring_enabled and inputs.ops_config.policy_gates.enable_verifier_programme
    )

    return SafetyReport(
        system_mode=system_mode,
        scoring_enabled=scoring_enabled,
        evidence_uploads_enabled=evidence_uploads_enabled,
        verifier_programme_enabled=verifier_programme_enabled,
        procurement_signals_stale=procurement_signals_stale,
        active_disputes=inputs.active_disputes,
        queue=inputs.queue,
        public_banner_messages=tuple(banners),
    )


def load_runtime_safety_inputs(
    registry_dir: Path,
    ops_dir: Path,
    ingestion_status: str,
) -> RuntimeSafetyInputs:
    """Load runtime inputs for the safety controller from local files."""
    validate_registry_dir(registry_dir)
    ops_config = load_ops_config(ops_dir)
    normalized_ingestion_status = _parse_ingestion_status(ingestion_status)
    return RuntimeSafetyInputs(
        ops_config=ops_config,
        queue=_load_queue_snapshot(registry_dir),
        active_disputes=_load_active_disputes(registry_dir),
        ingestion_status=normalized_ingestion_status,
    )


def _load_queue_snapshot(registry_dir: Path) -> QueueSnapshot:
    claims = len(list((registry_dir / "claims").glob("*.json")))
    disputes = len(
        [
            dispute
            for dispute in _load_lane(registry_dir / "disputes")
            if str(dispute.get("state")) in {"submitted", "under_review"}
        ]
    )
    return QueueSnapshot(
        claims=claims,
        corrections=0,
        disputes=disputes,
        verifications=0,
    )


def _load_active_disputes(registry_dir: Path) -> tuple[str, ...]:
    active_business_ids = sorted(
        {
            str(dispute["btr_id"])
            for dispute in _load_lane(registry_dir / "disputes")
            if str(dispute.get("state")) in {"submitted", "under_review"}
        }
    )
    return tuple(active_business_ids)


def _load_lane(directory: Path) -> tuple[dict[str, object], ...]:
    if not directory.exists():
        return ()
    documents: list[dict[str, object]] = []
    for file_path in sorted(directory.glob("*.json")):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{file_path} must contain a top-level JSON object")
        documents.append(_coerce_mapping(data))
    return tuple(documents)


def _coerce_mapping(value: dict[str, Any]) -> dict[str, object]:
    return {str(key): item for key, item in value.items()}


def _parse_ingestion_status(value: str) -> IngestionStatusName:
    normalized = value.strip().lower()
    allowed = {"healthy", "stale", "failed"}
    if normalized not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"ingestion status must be one of: {allowed_values}")
    return cast(IngestionStatusName, normalized)
