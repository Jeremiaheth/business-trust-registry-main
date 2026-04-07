"""Load machine-readable policy and governance configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class OpsConfigLoadError(ValueError):
    """Raised when policy configuration files cannot be loaded."""


@dataclass(frozen=True, slots=True)
class OwnerAssignments:
    """Named owners responsible for safety-critical functions."""

    moderation: str
    privacy_escalation: str
    verifier_approvals: str
    incident_response: str


@dataclass(frozen=True, slots=True)
class PolicyGates:
    """Boolean feature gates for risky capabilities."""

    enable_public_disputes: bool
    enable_third_party_complaints: bool
    enable_verifier_programme: bool
    enable_evidence_uploads: bool


@dataclass(frozen=True, slots=True)
class SafetyPolicy:
    """Thresholds that control safe operating mode."""

    backlog_warning_threshold: int
    maintenance_mode_threshold: int
    cooling_off_hours: int


@dataclass(frozen=True, slots=True)
class PrivacyPosture:
    """Machine-readable statement of what the public lane accepts."""

    public_repo_accepts_personal_data: bool
    public_repo_accepts_evidence_uploads: bool
    public_repo_accepts_public_disputes: bool
    allowed_public_submission_kinds: tuple[str, ...]
    private_lane_status: str


@dataclass(frozen=True, slots=True)
class OpsConfig:
    """Aggregated governance configuration."""

    owners: OwnerAssignments
    policy_gates: PolicyGates
    safety_policy: SafetyPolicy
    privacy_posture: PrivacyPosture


def load_ops_config(ops_dir: Path) -> OpsConfig:
    """Load the full operations configuration bundle from a directory."""
    owners_data = _load_yaml_mapping(ops_dir / "owners.yml")
    gates_data = _load_yaml_mapping(ops_dir / "policy_gates.yml")
    safety_data = _load_json_mapping(ops_dir / "safety_policy.json")
    privacy_data = _load_json_mapping(ops_dir / "privacy_posture.json")

    owners = OwnerAssignments(
        moderation=_load_string(owners_data, "moderation", "owners.yml"),
        privacy_escalation=_load_string(owners_data, "privacy_escalation", "owners.yml"),
        verifier_approvals=_load_string(owners_data, "verifier_approvals", "owners.yml"),
        incident_response=_load_string(owners_data, "incident_response", "owners.yml"),
    )
    policy_gates = PolicyGates(
        enable_public_disputes=_load_bool(
            gates_data, "enable_public_disputes", "policy_gates.yml"
        ),
        enable_third_party_complaints=_load_bool(
            gates_data, "enable_third_party_complaints", "policy_gates.yml"
        ),
        enable_verifier_programme=_load_bool(
            gates_data, "enable_verifier_programme", "policy_gates.yml"
        ),
        enable_evidence_uploads=_load_bool(
            gates_data, "enable_evidence_uploads", "policy_gates.yml"
        ),
    )
    safety_policy = SafetyPolicy(
        backlog_warning_threshold=_load_int(
            safety_data, "backlog_warning_threshold", "safety_policy.json"
        ),
        maintenance_mode_threshold=_load_int(
            safety_data, "maintenance_mode_threshold", "safety_policy.json"
        ),
        cooling_off_hours=_load_int(safety_data, "cooling_off_hours", "safety_policy.json"),
    )
    privacy_posture = PrivacyPosture(
        public_repo_accepts_personal_data=_load_bool(
            privacy_data, "public_repo_accepts_personal_data", "privacy_posture.json"
        ),
        public_repo_accepts_evidence_uploads=_load_bool(
            privacy_data, "public_repo_accepts_evidence_uploads", "privacy_posture.json"
        ),
        public_repo_accepts_public_disputes=_load_bool(
            privacy_data, "public_repo_accepts_public_disputes", "privacy_posture.json"
        ),
        allowed_public_submission_kinds=_load_string_list(
            privacy_data, "allowed_public_submission_kinds", "privacy_posture.json"
        ),
        private_lane_status=_load_string(
            privacy_data, "private_lane_status", "privacy_posture.json"
        ),
    )
    return OpsConfig(
        owners=owners,
        policy_gates=policy_gates,
        safety_policy=safety_policy,
        privacy_posture=privacy_posture,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    return _require_mapping(_load_file(path, yaml.safe_load), path.name)


def _load_json_mapping(path: Path) -> dict[str, Any]:
    return _require_mapping(_load_file(path, json.loads), path.name)


def _load_file(path: Path, loader: Any) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise OpsConfigLoadError(f"missing required config file: {path}") from error

    try:
        return loader(text)
    except Exception as error:  # pragma: no cover - exact parser exception is unimportant
        raise OpsConfigLoadError(f"failed to parse {path.name}: {error}") from error


def _require_mapping(value: Any, source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OpsConfigLoadError(f"{source} must contain a top-level mapping")
    return value


def _load_string(data: dict[str, Any], key: str, source: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise OpsConfigLoadError(f"{source} field '{key}' must be a string")
    return value.strip()


def _load_bool(data: dict[str, Any], key: str, source: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise OpsConfigLoadError(f"{source} field '{key}' must be a boolean")
    return value


def _load_int(data: dict[str, Any], key: str, source: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise OpsConfigLoadError(f"{source} field '{key}' must be an integer")
    return value


def _load_string_list(data: dict[str, Any], key: str, source: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise OpsConfigLoadError(f"{source} field '{key}' must be a list of strings")

    cleaned = tuple(item.strip() for item in value)
    if any(not item for item in cleaned):
        raise OpsConfigLoadError(f"{source} field '{key}' must not contain empty strings")
    return cleaned
