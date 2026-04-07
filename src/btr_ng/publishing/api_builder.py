"""Build static public API artifacts for GitHub Pages."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from btr_ng.ingestion.quality import load_procurement_status
from btr_ng.registry.validator import RegistryValidationError, validate_registry_dir
from btr_ng.schema import SchemaValidationError, validate_document


class ApiBuildError(ValueError):
    """Raised when static API artifacts cannot be built safely."""


def build_public_api(
    registry_dir: Path,
    score_dir: Path,
    out_dir: Path,
    derived_dir: Path | None = None,
) -> int:
    """Build deterministic public API artifacts from validated upstream inputs."""
    try:
        validate_registry_dir(registry_dir)
    except RegistryValidationError as error:
        raise ApiBuildError(str(error)) from error

    businesses = _load_objects(registry_dir / "businesses")
    evidence_items = _load_objects(registry_dir / "evidence")
    disputes = _load_objects(registry_dir / "disputes")
    scores = _load_score_snapshots(score_dir)
    derived_records = _load_derived_records(derived_dir) if derived_dir is not None else {}
    procurement_status = load_procurement_status(derived_dir)

    business_ids = tuple(sorted(str(business["btr_id"]) for business in businesses))
    _ensure_score_coverage(business_ids, scores)

    evidence_by_business = _group_evidence_by_business(evidence_items)
    disputes_by_business = _group_disputes_by_business(disputes)
    generated_at = _determine_generated_at(scores)

    businesses_dir = out_dir / "businesses"
    manifests_dir = out_dir / "manifests"
    businesses_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, object]] = []
    index_items: list[dict[str, object]] = []
    search_entries: list[dict[str, object]] = []

    for business in sorted(businesses, key=lambda item: str(item["btr_id"])):
        btr_id = str(business["btr_id"])
        business_document = {
            "btr_id": btr_id,
            "generated_at": generated_at,
            "profile": business,
            "score": scores[btr_id],
            "procurement_data_status": procurement_status,
            "evidence": evidence_by_business.get(btr_id, []),
            "disputes": disputes_by_business.get(btr_id, []),
            "derived_records": derived_records.get(btr_id, []),
        }
        business_path = businesses_dir / f"{btr_id}.json"
        _write_json(business_path, business_document)
        artifacts.append(_artifact_metadata(out_dir, business_path, "business"))
        index_items.append(_build_index_entry(business, scores[btr_id]))
        search_entries.append(
            _build_search_entry(
                business=business,
                score=scores[btr_id],
                evidence=evidence_by_business.get(btr_id, []),
            )
        )

    index_document = {
        "generated_at": generated_at,
        "procurement_data_status": procurement_status,
        "counts": {
            "businesses": len(businesses),
            "evidence": len(evidence_items),
            "open_disputes": sum(
                1 for dispute in disputes if str(dispute.get("state")) == "under_review"
            ),
        },
        "items": index_items,
    }
    index_path = out_dir / "index.json"
    _write_json(index_path, index_document)
    artifacts.append(_artifact_metadata(out_dir, index_path, "index"))

    search_document = {
        "generated_at": generated_at,
        "entries": search_entries,
    }
    search_path = out_dir / "search.json"
    _write_json(search_path, search_document)
    artifacts.append(_artifact_metadata(out_dir, search_path, "search"))

    manifest_document = {
        "generated_at": generated_at,
        "artifact_count": len(artifacts),
        "artifacts": sorted(artifacts, key=lambda item: str(item["path"])),
    }
    _write_json(manifests_dir / "latest.json", manifest_document)
    return len(artifacts) + 1


def _load_score_snapshots(score_dir: Path) -> dict[str, dict[str, object]]:
    if not score_dir.exists():
        raise ApiBuildError(f"score directory does not exist: {score_dir}")
    if not score_dir.is_dir():
        raise ApiBuildError(f"score path must be a directory: {score_dir}")

    snapshots: dict[str, dict[str, object]] = {}
    for file_path in sorted(score_dir.glob("*.json")):
        document = _load_json_object(file_path)
        try:
            validate_document("trust-score", document)
        except SchemaValidationError as error:
            raise ApiBuildError(f"{file_path}: invalid trust score snapshot: {error}") from error

        btr_id = str(document["btr_id"])
        if btr_id in snapshots:
            raise ApiBuildError(f"duplicate trust score snapshot for {btr_id}")
        snapshots[btr_id] = document

    if not snapshots:
        raise ApiBuildError(f"no score snapshots found in {score_dir}")
    return snapshots


def _load_objects(directory: Path) -> tuple[dict[str, object], ...]:
    if not directory.exists():
        return ()
    if not directory.is_dir():
        raise ApiBuildError(f"expected a directory at {directory}")

    documents: list[dict[str, object]] = []
    for file_path in sorted(directory.glob("*.json")):
        documents.append(_load_json_object(file_path))
    return tuple(documents)


def _load_derived_records(derived_dir: Path) -> dict[str, list[dict[str, object]]]:
    if not derived_dir.exists():
        return {}
    if not derived_dir.is_dir():
        raise ApiBuildError(f"derived path must be a directory: {derived_dir}")

    records_by_business: dict[str, list[dict[str, object]]] = {}
    for file_path in sorted(derived_dir.rglob("*.json")):
        document = _load_json_object(file_path)
        btr_id = document.get("btr_id")
        if not isinstance(btr_id, str):
            continue

        records_by_business.setdefault(btr_id, []).append(
            {
                "path": file_path.relative_to(derived_dir).as_posix(),
                "document": document,
            }
        )
    return records_by_business


def _group_evidence_by_business(
    evidence_items: tuple[dict[str, object], ...],
) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for evidence in evidence_items:
        related = evidence.get("related_businesses", [])
        if not isinstance(related, list):
            continue
        for business_id in related:
            grouped.setdefault(str(business_id), []).append(evidence)
    return grouped


def _group_disputes_by_business(
    disputes: tuple[dict[str, object], ...],
) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for dispute in disputes:
        grouped.setdefault(str(dispute["btr_id"]), []).append(dispute)
    return grouped


def _ensure_score_coverage(
    business_ids: tuple[str, ...],
    scores: dict[str, dict[str, object]],
) -> None:
    missing = sorted(btr_id for btr_id in business_ids if btr_id not in scores)
    extra = sorted(btr_id for btr_id in scores if btr_id not in business_ids)
    if missing:
        raise ApiBuildError(
            "missing trust score snapshots for: " + ", ".join(missing)
        )
    if extra:
        raise ApiBuildError(
            "unexpected trust score snapshots for unknown businesses: " + ", ".join(extra)
        )


def _determine_generated_at(scores: dict[str, dict[str, object]]) -> str:
    timestamps = [
        _parse_datetime(str(snapshot["generated_at"]))
        for snapshot in scores.values()
    ]
    return max(timestamps).isoformat().replace("+00:00", "Z")


def _build_index_entry(
    business: dict[str, object],
    score: dict[str, object],
) -> dict[str, object]:
    return {
        "btr_id": str(business["btr_id"]),
        "legal_name": str(business["legal_name"]),
        "trading_name": str(business.get("trading_name", "")),
        "jurisdiction": str(business["jurisdiction"]),
        "record_state": str(business["record_state"]),
        "score": score["score"],
        "confidence": score["confidence"],
        "band": score["band"],
        "status": score["status"],
        "display_state": score["display_state"],
        "public_note": score["public_note"],
        "verification_timestamp": score["verification_timestamp"],
    }


def _build_search_entry(
    business: dict[str, object],
    score: dict[str, object],
    evidence: list[dict[str, object]],
) -> dict[str, object]:
    identifiers = cast(dict[str, object], business.get("identifiers", {}))
    tags: set[str] = set()
    terms: set[str] = {
        str(business["btr_id"]).lower(),
        str(business["legal_name"]).lower(),
        str(business["jurisdiction"]).lower(),
    }

    trading_name = business.get("trading_name")
    if isinstance(trading_name, str):
        terms.add(trading_name.lower())

    primary_identifier = identifiers.get("primary")
    if isinstance(primary_identifier, str):
        terms.add(primary_identifier.lower())

    secondary_identifiers = identifiers.get("secondary", [])
    if isinstance(secondary_identifiers, list):
        for value in secondary_identifiers:
            terms.add(str(value).lower())

    derived_signals = cast(dict[str, object], business.get("derived_signals", {}))
    flags = derived_signals.get("flags", [])
    if isinstance(flags, list):
        for flag in flags:
            flag_value = str(flag)
            tags.add(flag_value)
            terms.add(flag_value.lower())

    for evidence_item in evidence:
        evidence_tags = evidence_item.get("tags", [])
        if isinstance(evidence_tags, list):
            for tag in evidence_tags:
                tag_value = str(tag)
                tags.add(tag_value)
                terms.add(tag_value.lower())

    display_name = (
        str(trading_name)
        if isinstance(trading_name, str) and trading_name
        else str(business["legal_name"])
    )
    return {
        "btr_id": str(business["btr_id"]),
        "display_name": display_name,
        "legal_name": str(business["legal_name"]),
        "trading_name": str(trading_name) if isinstance(trading_name, str) else "",
        "jurisdiction": str(business["jurisdiction"]),
        "display_state": score["display_state"],
        "tags": sorted(tags),
        "terms": sorted(terms),
    }


def _artifact_metadata(out_dir: Path, artifact_path: Path, artifact_type: str) -> dict[str, object]:
    content = artifact_path.read_bytes()
    return {
        "path": artifact_path.relative_to(out_dir).as_posix(),
        "type": artifact_type,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json_object(file_path: Path) -> dict[str, object]:
    try:
        document = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ApiBuildError(f"{file_path}: invalid JSON: {error.msg}") from error

    if not isinstance(document, dict):
        raise ApiBuildError(f"{file_path}: expected a top-level JSON object")
    return cast(dict[str, object], document)


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
