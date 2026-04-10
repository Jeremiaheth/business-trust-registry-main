"""Build static public API artifacts for GitHub Pages."""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from btr_ng.ingestion.quality import load_procurement_status
from btr_ng.publishing.presentation import (
    build_business_presentation,
    build_directory_filters,
    build_index_entry,
    build_report_document,
    build_search_entry,
)
from btr_ng.registry.validator import RegistryValidationError, validate_registry_dir
from btr_ng.release import ReleaseManifestError, write_release_manifest
from btr_ng.safety.controller import build_safety_report, load_runtime_safety_inputs
from btr_ng.safety.queue_status import build_queue_status_artifact
from btr_ng.schema import SchemaValidationError, validate_document


class ApiBuildError(ValueError):
    """Raised when static API artifacts cannot be built safely."""


def build_public_api(
    registry_dir: Path,
    score_dir: Path,
    out_dir: Path,
    derived_dir: Path | None = None,
    ops_dir: Path = Path("ops"),
    ingestion_status: str = "healthy",
) -> int:
    """Build deterministic public API artifacts from validated upstream inputs."""
    if out_dir.exists():
        if not out_dir.is_dir():
            raise ApiBuildError(f"public API output path must be a directory: {out_dir}")
        for child in out_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

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
    safety_report = build_safety_report(
        load_runtime_safety_inputs(
            registry_dir=registry_dir,
            ops_dir=ops_dir,
            ingestion_status=ingestion_status,
        )
    )
    queue_status = build_queue_status_artifact(
        registry_dir=registry_dir,
        generated_at=generated_at,
        safety_report=safety_report,
        stale_override=bool(procurement_status.get("stale", False)),
    )

    businesses_dir = out_dir / "businesses"
    reports_dir = out_dir / "reports"
    manifests_dir = out_dir / "manifests"
    businesses_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths: list[Path] = []
    artifact_types: dict[str, str] = {}
    index_items: list[dict[str, object]] = []
    search_entries: list[dict[str, object]] = []

    for business in sorted(businesses, key=lambda item: str(item["btr_id"])):
        btr_id = str(business["btr_id"])
        business_evidence = evidence_by_business.get(btr_id, [])
        business_disputes = disputes_by_business.get(btr_id, [])
        business_derived_records = derived_records.get(btr_id, [])
        presentation = build_business_presentation(
            business=business,
            score=scores[btr_id],
            evidence=business_evidence,
            disputes=business_disputes,
            derived_records=business_derived_records,
        )
        business_document = {
            "btr_id": btr_id,
            "generated_at": generated_at,
            "profile": business,
            "score": scores[btr_id],
            "procurement_data_status": procurement_status,
            "evidence": business_evidence,
            "disputes": business_disputes,
            "derived_records": business_derived_records,
            "presentation": presentation,
        }
        business_path = businesses_dir / f"{btr_id}.json"
        _write_json(business_path, business_document)
        artifact_paths.append(business_path)
        artifact_types[business_path.relative_to(out_dir).as_posix()] = "business"
        index_items.append(build_index_entry(business, scores[btr_id], business_evidence))
        search_entries.append(
            build_search_entry(
                business=business,
                score=scores[btr_id],
                evidence=business_evidence,
            )
        )
        report_document = build_report_document(
            business=business,
            score=scores[btr_id],
            evidence=business_evidence,
            disputes=business_disputes,
            derived_records=business_derived_records,
            generated_at=generated_at,
        )
        report_path = reports_dir / f"{btr_id}.json"
        _write_json(report_path, report_document)
        artifact_paths.append(report_path)
        artifact_types[report_path.relative_to(out_dir).as_posix()] = "report"

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
        "filters": build_directory_filters(index_items),
        "items": index_items,
    }
    index_path = out_dir / "index.json"
    _write_json(index_path, index_document)
    artifact_paths.append(index_path)
    artifact_types[index_path.relative_to(out_dir).as_posix()] = "index"

    queue_status_path = out_dir / "queue_status.json"
    _write_json(queue_status_path, queue_status.to_dict())
    artifact_paths.append(queue_status_path)
    artifact_types[queue_status_path.relative_to(out_dir).as_posix()] = "queue_status"

    search_document = {
        "generated_at": generated_at,
        "filters": build_directory_filters(index_items),
        "entries": search_entries,
    }
    search_path = out_dir / "search.json"
    _write_json(search_path, search_document)
    artifact_paths.append(search_path)
    artifact_types[search_path.relative_to(out_dir).as_posix()] = "search"

    try:
        manifest_document = write_release_manifest(
            artifact_root=out_dir,
            artifact_paths=artifact_paths,
            manifest_path=manifests_dir / "latest.json",
            generated_at=generated_at,
            artifact_types=artifact_types,
        )
    except ReleaseManifestError as error:
        raise ApiBuildError(str(error)) from error
    artifact_count = manifest_document.get("artifact_count")
    if not isinstance(artifact_count, int):
        raise ApiBuildError("release manifest artifact_count must be an integer")
    return artifact_count + 1


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
