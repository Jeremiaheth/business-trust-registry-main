"""Validation rules for ops configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from btr_ng.policy.config import OpsConfig, OpsConfigLoadError, load_ops_config

REQUIRED_OWNER_FIELDS = (
    "moderation",
    "privacy_escalation",
    "verifier_approvals",
    "incident_response",
)

DANGEROUS_GATE_OWNERS = {
    "enable_public_disputes": "moderation",
    "enable_third_party_complaints": "moderation",
    "enable_verifier_programme": "verifier_approvals",
    "enable_evidence_uploads": "privacy_escalation",
}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single actionable configuration problem."""

    source: str
    message: str

    def render(self) -> str:
        """Return a user-facing error string."""
        return f"{self.source}: {self.message}"


class OpsValidationError(ValueError):
    """Raised when ops validation fails."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        joined = "; ".join(issue.render() for issue in issues)
        super().__init__(joined)


def validate_ops_dir(ops_dir: Path) -> OpsConfig:
    """Load and validate ops configuration from disk."""
    try:
        config = load_ops_config(ops_dir)
    except OpsConfigLoadError as error:
        raise OpsValidationError([ValidationIssue("ops", str(error))]) from error

    issues = validate_ops_config(config)
    if issues:
        raise OpsValidationError(issues)
    return config


def validate_ops_config(config: OpsConfig) -> list[ValidationIssue]:
    """Validate the semantic safety rules for ops configuration."""
    issues: list[ValidationIssue] = []

    for owner_field in REQUIRED_OWNER_FIELDS:
        owner_value = getattr(config.owners, owner_field)
        if not owner_value:
            issues.append(
                ValidationIssue(
                    "owners.yml",
                    f"required owner '{owner_field}' must be assigned.",
                )
            )

    for gate_name, owner_field in DANGEROUS_GATE_OWNERS.items():
        gate_enabled = getattr(config.policy_gates, gate_name)
        owner_value = getattr(config.owners, owner_field)
        if gate_enabled and not owner_value:
            issues.append(
                ValidationIssue(
                    "policy_gates.yml",
                    (
                        f"'{gate_name}' cannot be enabled without assigning "
                        f"'{owner_field}' in owners.yml."
                    ),
                )
            )

    if config.privacy_posture.public_repo_accepts_personal_data:
        issues.append(
            ValidationIssue(
                "privacy_posture.json",
                "public_repo_accepts_personal_data must remain false for the public repo.",
            )
        )

    if (
        config.policy_gates.enable_evidence_uploads
        != config.privacy_posture.public_repo_accepts_evidence_uploads
    ):
        issues.append(
            ValidationIssue(
                "privacy_posture.json",
                "public evidence upload posture must match the enable_evidence_uploads gate.",
            )
        )

    if (
        config.policy_gates.enable_public_disputes
        != config.privacy_posture.public_repo_accepts_public_disputes
    ):
        issues.append(
            ValidationIssue(
                "privacy_posture.json",
                "public dispute posture must match the enable_public_disputes gate.",
            )
        )

    if config.safety_policy.backlog_warning_threshold <= 0:
        issues.append(
            ValidationIssue(
                "safety_policy.json",
                "backlog_warning_threshold must be greater than zero.",
            )
        )

    if (
        config.safety_policy.maintenance_mode_threshold
        <= config.safety_policy.backlog_warning_threshold
    ):
        issues.append(
            ValidationIssue(
                "safety_policy.json",
                "maintenance_mode_threshold must be greater than backlog_warning_threshold.",
            )
        )

    if config.safety_policy.cooling_off_hours < 0:
        issues.append(
            ValidationIssue(
                "safety_policy.json",
                "cooling_off_hours must be zero or greater.",
            )
        )

    if not config.privacy_posture.allowed_public_submission_kinds:
        issues.append(
            ValidationIssue(
                "privacy_posture.json",
                "allowed_public_submission_kinds must include at least one public-safe flow.",
            )
        )

    if config.privacy_posture.private_lane_status not in {"deferred", "pilot", "active"}:
        issues.append(
            ValidationIssue(
                "privacy_posture.json",
                "private_lane_status must be one of: deferred, pilot, active.",
            )
        )

    return issues
