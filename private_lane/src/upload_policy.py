"""Upload policy decisions for the private lane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class UploadDecision:
    """A deterministic upload policy decision."""

    allowed: bool
    reasons: tuple[str, ...]


def decide_upload_policy(
    policy_gates: dict[str, Any],
    privacy_posture: dict[str, Any],
    safety_report: dict[str, Any],
) -> UploadDecision:
    """Decide whether private-lane uploads may proceed."""
    reasons: list[str] = []

    if not bool(policy_gates.get("enable_evidence_uploads", False)):
        reasons.append("policy gates disable evidence uploads")

    if str(privacy_posture.get("private_lane_status", "deferred")) != "enabled":
        reasons.append("privacy posture does not enable private-lane evidence storage")

    if not bool(safety_report.get("evidence_uploads_enabled", False)):
        reasons.append("safety controller does not permit evidence uploads")

    if str(safety_report.get("system_mode", "NORMAL")).upper() == "MAINTENANCE":
        reasons.append("system is in maintenance mode")

    return UploadDecision(allowed=not reasons, reasons=tuple(reasons))
