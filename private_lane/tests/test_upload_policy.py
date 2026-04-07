from __future__ import annotations

import hashlib

from cases import create_case
from storage import R2ManifestStorageAdapter, build_evidence_manifest
from upload_policy import decide_upload_policy


def test_uploads_are_rejected_by_default() -> None:
    decision = decide_upload_policy(
        policy_gates={"enable_evidence_uploads": False},
        privacy_posture={"private_lane_status": "deferred"},
        safety_report={"evidence_uploads_enabled": False, "system_mode": "NORMAL"},
    )

    assert decision.allowed is False
    assert decision.reasons == (
        "policy gates disable evidence uploads",
        "privacy posture does not enable private-lane evidence storage",
        "safety controller does not permit evidence uploads",
    )


def test_policy_driven_acceptance_path_uses_mock_adapter_only() -> None:
    class FakeBucket:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bytes, dict[str, str] | None, dict[str, str] | None]] = []

        def put(
            self,
            key: str,
            value: bytes,
            *,
            http_metadata: dict[str, str] | None = None,
            custom_metadata: dict[str, str] | None = None,
        ) -> object:
            self.calls.append((key, value, http_metadata, custom_metadata))
            return {"key": key}

    decision = decide_upload_policy(
        policy_gates={"enable_evidence_uploads": True},
        privacy_posture={"private_lane_status": "enabled"},
        safety_report={"evidence_uploads_enabled": True, "system_mode": "NORMAL"},
    )
    assert decision.allowed is True

    case = create_case(
        {
            "case_id": "CASE-101",
            "kind": "verification",
            "redacted_summary": "Public-safe summary for a future evidence upload path.",
            "evidence_references": [
                {"kind": "url", "value": "https://example.com/evidence"},
            ],
        },
        now="2026-04-07T18:00:00Z",
    )
    manifest = build_evidence_manifest(
        case=case,
        generated_at="2026-04-07T18:10:00Z",
        retention_days=30,
    )

    bucket = FakeBucket()
    adapter = R2ManifestStorageAdapter(bucket)
    key = adapter.store_manifest(manifest)

    assert key == "evidence-manifests/evidence-pack-case-101.json"
    assert len(bucket.calls) == 1
    assert bucket.calls[0][2] == {"content-type": "application/json; charset=utf-8"}
    assert bucket.calls[0][3] == {"evidence_pack_id": "evidence-pack-case-101"}


def test_manifest_generation_from_link_only_submission() -> None:
    case = create_case(
        {
            "case_id": "CASE-102",
            "kind": "claim",
            "redacted_summary": "Public-safe summary for a link-only evidence manifest.",
            "evidence_references": [
                {"kind": "url", "value": "https://example.com/claim"},
                {"kind": "hash", "value": "0123456789abcdef0123456789abcdef"},
            ],
        },
        now="2026-04-07T18:00:00Z",
    )

    manifest = build_evidence_manifest(
        case=case,
        generated_at="2026-04-07T18:30:00Z",
        retention_days=45,
    )

    expected_hashes = sorted(
        [
            hashlib.sha256(b"url:https://example.com/claim").hexdigest(),
            hashlib.sha256(b"hash:0123456789abcdef0123456789abcdef").hexdigest(),
        ]
    )
    assert manifest.document == {
        "evidence_pack_id": "evidence-pack-case-102",
        "case_id": "CASE-102",
        "generated_at": "2026-04-07T18:30:00Z",
        "item_hashes": expected_hashes,
        "retention": {
            "retention_days": 45,
            "review_mode": "link_only",
        },
        "storage": {
            "backend": "r2_placeholder",
            "bucket": "pending-provisioning",
            "object_keys": [],
            "encryption": {
                "status": "placeholder",
                "key_reference": None,
            },
        },
    }
