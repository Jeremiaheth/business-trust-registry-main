"""Storage adapter abstractions for private-lane evidence manifests."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from models import PrivateCase


class StorageAdapterError(ValueError):
    """Raised when storage adapter operations cannot proceed safely."""


class R2BucketLike(Protocol):
    """Minimal R2 bucket protocol needed for manifest storage."""

    def put(
        self,
        key: str,
        value: bytes,
        *,
        http_metadata: dict[str, str] | None = None,
        custom_metadata: dict[str, str] | None = None,
    ) -> object:
        """Store bytes under a key."""


@dataclass(frozen=True, slots=True)
class EvidenceManifest:
    """A public-safe evidence manifest placeholder for future storage flows."""

    evidence_pack_id: str
    document: dict[str, object]


def build_evidence_manifest(
    case: PrivateCase,
    generated_at: str,
    retention_days: int,
) -> EvidenceManifest:
    """Build a deterministic evidence manifest from a link-only case record."""
    if retention_days < 1:
        raise StorageAdapterError("retention_days must be at least 1")

    item_hashes = sorted(
        hashlib.sha256(f"{reference.kind}:{reference.value}".encode()).hexdigest()
        for reference in case.evidence_references
    )
    evidence_pack_id = f"evidence-pack-{case.case_id.lower()}"
    document = {
        "evidence_pack_id": evidence_pack_id,
        "case_id": case.case_id,
        "generated_at": generated_at,
        "item_hashes": item_hashes,
        "retention": {
            "retention_days": retention_days,
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
    return EvidenceManifest(evidence_pack_id=evidence_pack_id, document=document)


class R2ManifestStorageAdapter:
    """Mockable R2 adapter for evidence manifest storage."""

    def __init__(self, bucket: R2BucketLike, prefix: str = "evidence-manifests") -> None:
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    def store_manifest(self, manifest: EvidenceManifest) -> str:
        """Store an evidence manifest JSON document in R2-compatible storage."""
        evidence_pack_id = manifest.document.get("evidence_pack_id")
        if evidence_pack_id != manifest.evidence_pack_id:
            raise StorageAdapterError("manifest evidence_pack_id must match the container object")

        key = f"{self._prefix}/{manifest.evidence_pack_id}.json"
        payload = json.dumps(manifest.document, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        self._bucket.put(
            key,
            payload,
            http_metadata={"content-type": "application/json; charset=utf-8"},
            custom_metadata={"evidence_pack_id": manifest.evidence_pack_id},
        )
        return key


def manifest_from_mapping(document: Mapping[str, object]) -> EvidenceManifest:
    """Reconstruct an EvidenceManifest from an existing mapping."""
    evidence_pack_id = document.get("evidence_pack_id")
    if not isinstance(evidence_pack_id, str) or not evidence_pack_id:
        raise StorageAdapterError("manifest mapping must include a non-empty evidence_pack_id")
    return EvidenceManifest(evidence_pack_id=evidence_pack_id, document=dict(document))
