"""Typed helpers for public dispute records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from btr_ng.schema import validate_document


@dataclass(frozen=True, slots=True)
class PublicDisputeRecord:
    """Typed public dispute record."""

    case_id: str
    btr_id: str
    review_type: str
    state: str
    redacted_summary: str
    evidence_pack_refs: tuple[str, ...]
    opened_at: str
    updated_at: str
    resolution_note: str | None

    @property
    def is_active(self) -> bool:
        """Return whether the dispute should suppress normal public scoring."""
        return self.state in {"submitted", "under_review"}


def load_dispute_records(directory: Path) -> tuple[PublicDisputeRecord, ...]:
    """Load and validate public dispute records from a registry directory."""
    if not directory.exists():
        return ()
    records: list[PublicDisputeRecord] = []
    for file_path in sorted(directory.glob("*.json")):
        data = _load_json_object(file_path)
        validate_document("dispute-record", data)
        records.append(
            PublicDisputeRecord(
                case_id=str(data["case_id"]),
                btr_id=str(data["btr_id"]),
                review_type=str(data["review_type"]),
                state=str(data["state"]),
                redacted_summary=str(data["redacted_summary"]),
                evidence_pack_refs=tuple(
                    str(item) for item in cast(list[object], data["evidence_pack_refs"])
                ),
                opened_at=str(data["opened_at"]),
                updated_at=str(data["updated_at"]),
                resolution_note=(
                    str(data["resolution_note"])
                    if "resolution_note" in data and data["resolution_note"] is not None
                    else None
                ),
            )
        )
    return tuple(records)


def active_dispute_business_ids(records: tuple[PublicDisputeRecord, ...]) -> tuple[str, ...]:
    """Return business IDs currently under active dispute review."""
    return tuple(sorted({record.btr_id for record in records if record.is_active}))


def active_dispute_updates(records: tuple[PublicDisputeRecord, ...]) -> dict[str, str]:
    """Return the latest active dispute timestamp per business."""
    updates: dict[str, str] = {}
    for record in records:
        if not record.is_active:
            continue
        existing = updates.get(record.btr_id)
        if existing is None or record.updated_at > existing:
            updates[record.btr_id] = record.updated_at
    return updates


def _load_json_object(file_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{file_path}: invalid JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{file_path}: expected a top-level JSON object")
    return cast(dict[str, object], payload)
