"""Quality and staleness reporting for procurement ingestion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast


class IngestionQualityError(ValueError):
    """Raised when an ingestion quality report cannot be produced."""


@dataclass(frozen=True, slots=True)
class IngestionQualityReport:
    """Deterministic report for procurement ingestion quality."""

    source: str
    source_input: str
    generated_at: str
    ingestion_status: str
    release_count: int
    supplier_count: int
    matched_record_count: int
    buyer_count: int
    contracts_count: int
    latest_source_timestamp: str
    stale: bool
    staleness_reason: str
    anomaly_count: int
    anomalies: tuple[str, ...]
    mapping_warning_count: int
    mapping_warnings: tuple[str, ...]
    max_age_days: int
    public_note: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "source": self.source,
            "source_input": self.source_input,
            "generated_at": self.generated_at,
            "ingestion_status": self.ingestion_status,
            "release_count": self.release_count,
            "supplier_count": self.supplier_count,
            "matched_record_count": self.matched_record_count,
            "buyer_count": self.buyer_count,
            "contracts_count": self.contracts_count,
            "latest_source_timestamp": self.latest_source_timestamp,
            "stale": self.stale,
            "staleness_reason": self.staleness_reason,
            "anomaly_count": self.anomaly_count,
            "anomalies": list(self.anomalies),
            "mapping_warning_count": self.mapping_warning_count,
            "mapping_warnings": list(self.mapping_warnings),
            "max_age_days": self.max_age_days,
            "public_note": self.public_note,
        }


def build_nocopo_quality_report(
    input_path: Path,
    derived_dir: Path,
    out_dir: Path,
    ingestion_status: str,
    max_age_days: int = 30,
    evaluated_at: datetime | None = None,
) -> IngestionQualityReport:
    """Build and persist a deterministic quality report for NOCOPO ingestion."""
    if max_age_days < 1:
        raise IngestionQualityError("max_age_days must be at least 1")
    if ingestion_status not in {"healthy", "stale", "failed"}:
        raise IngestionQualityError("ingestion_status must be one of: healthy, stale, failed")

    package = _load_json_object(input_path)
    releases = _load_releases(package)
    if not releases:
        raise IngestionQualityError("fixture does not contain any OCDS releases")

    derived_records = _load_derived_records(derived_dir)
    release_count = len(releases)
    buyer_names = {buyer for buyer in (_buyer_name(release) for release in releases)}
    supplier_count = len(_distinct_suppliers(releases))
    contracts_count = sum(_contracts_count(release) for release in releases)
    matched_record_count = len(derived_records)
    latest_source_timestamp_dt = _package_timestamp(package, releases)
    evaluated_at_value = evaluated_at or datetime.now(UTC)
    age_days = (evaluated_at_value - latest_source_timestamp_dt).total_seconds() / 86400.0

    mapping_warnings: list[str] = []
    if matched_record_count < supplier_count:
        mapping_warnings.append(
            
                f"{supplier_count - matched_record_count} supplier entries could not be "
                "matched to a registry business."
            
        )

    anomalies: list[str] = []
    stale = False
    staleness_reason = ""
    if ingestion_status == "failed":
        stale = True
        staleness_reason = "ingestion_failed"
        anomalies.append("The most recent procurement ingestion run failed.")
    elif ingestion_status == "stale":
        stale = True
        staleness_reason = "ingestion_marked_stale"
        anomalies.append("The procurement ingestion status was marked stale by the operator.")
    elif age_days > max_age_days:
        stale = True
        staleness_reason = "source_snapshot_too_old"
        anomalies.append(
            f"The latest procurement source snapshot is older than {max_age_days} days."
        )

    public_note = (
        "Procurement-linked signals are current within the configured freshness window."
        if not stale
        else _stale_public_note(staleness_reason, max_age_days)
    )

    report = IngestionQualityReport(
        source="nocopo",
        source_input=input_path.name,
        generated_at=evaluated_at_value.isoformat().replace("+00:00", "Z"),
        ingestion_status=ingestion_status,
        release_count=release_count,
        supplier_count=supplier_count,
        matched_record_count=matched_record_count,
        buyer_count=len(buyer_names),
        contracts_count=contracts_count,
        latest_source_timestamp=latest_source_timestamp_dt.isoformat().replace("+00:00", "Z"),
        stale=stale,
        staleness_reason=staleness_reason,
        anomaly_count=len(anomalies),
        anomalies=tuple(anomalies),
        mapping_warning_count=len(mapping_warnings),
        mapping_warnings=tuple(mapping_warnings),
        max_age_days=max_age_days,
        public_note=public_note,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "nocopo_ingestion_report.json"
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def load_procurement_status(derived_dir: Path | None) -> dict[str, object]:
    """Load a stable procurement freshness payload for publishing layers."""
    default_status: dict[str, object] = {
        "available": False,
        "stale": False,
        "ingestion_status": "unknown",
        "staleness_reason": "",
        "latest_source_timestamp": "",
        "anomaly_count": 0,
        "mapping_warning_count": 0,
        "public_note": "No procurement ingestion report is available.",
    }
    if derived_dir is None:
        return default_status

    report_path = derived_dir / "reports" / "nocopo_ingestion_report.json"
    if not report_path.exists():
        return default_status

    report = _load_json_object(report_path)
    return {
        "available": True,
        "stale": bool(report.get("stale", False)),
        "ingestion_status": str(report.get("ingestion_status", "unknown")),
        "staleness_reason": str(report.get("staleness_reason", "")),
        "latest_source_timestamp": str(report.get("latest_source_timestamp", "")),
        "anomaly_count": int(report.get("anomaly_count", 0)),
        "mapping_warning_count": int(report.get("mapping_warning_count", 0)),
        "public_note": str(report.get("public_note", default_status["public_note"])),
    }


def _load_json_object(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise IngestionQualityError(f"input does not exist: {file_path}")
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise IngestionQualityError(f"{file_path}: invalid JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise IngestionQualityError(f"{file_path}: expected a top-level JSON object")
    return cast(dict[str, Any], payload)


def _load_releases(package: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    releases = package.get("releases")
    if not isinstance(releases, list):
        raise IngestionQualityError("fixture must contain a 'releases' list")
    return tuple(_ensure_object(release, "release") for release in releases)


def _package_timestamp(
    package: dict[str, Any],
    releases: tuple[dict[str, Any], ...],
) -> datetime:
    published_date = package.get("publishedDate")
    if isinstance(published_date, str) and published_date.strip():
        return _parse_datetime(published_date)
    return max(_release_date(release) for release in releases)


def _load_derived_records(derived_dir: Path) -> tuple[dict[str, Any], ...]:
    if not derived_dir.exists():
        return ()
    records: list[dict[str, Any]] = []
    for file_path in sorted(derived_dir.glob("*.json")):
        records.append(_load_json_object(file_path))
    return tuple(records)


def _distinct_suppliers(releases: tuple[dict[str, Any], ...]) -> set[str]:
    suppliers: set[str] = set()
    for release in releases:
        awards = release.get("awards", [])
        if not isinstance(awards, list):
            raise IngestionQualityError("release awards must be a list")
        for award in awards:
            award_object = _ensure_object(award, "award")
            award_suppliers = award_object.get("suppliers", [])
            if not isinstance(award_suppliers, list):
                raise IngestionQualityError("award suppliers must be a list")
            for supplier in award_suppliers:
                supplier_object = _ensure_object(supplier, "supplier")
                supplier_name = str(supplier_object.get("name", "")).strip()
                identifier = supplier_object.get("identifier", {})
                supplier_identifier = ""
                if isinstance(identifier, dict):
                    supplier_identifier = str(identifier.get("id", "")).strip()
                key = _normalize(supplier_identifier or supplier_name)
                if key:
                    suppliers.add(key)
    return suppliers


def _contracts_count(release: dict[str, Any]) -> int:
    contracts = release.get("contracts", [])
    if not isinstance(contracts, list):
        raise IngestionQualityError("release contracts must be a list")
    return len(contracts)


def _buyer_name(release: dict[str, Any]) -> str:
    buyer = release.get("buyer", {})
    if not isinstance(buyer, dict):
        raise IngestionQualityError("release buyer must be an object")
    buyer_name = str(buyer.get("name", "")).strip()
    if not buyer_name:
        raise IngestionQualityError("release buyer name is required")
    return buyer_name


def _release_date(release: dict[str, Any]) -> datetime:
    value = release.get("date")
    if not isinstance(value, str) or not value.strip():
        raise IngestionQualityError("release date is required")
    return _parse_datetime(value)


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _stale_public_note(reason: str, max_age_days: int) -> str:
    if reason == "ingestion_failed":
        return (
            "Procurement-linked signals may be stale because the most recent "
            "ingestion run failed."
        )
    if reason == "ingestion_marked_stale":
        return "Procurement-linked signals are marked stale pending a fresh ingestion run."
    return (
        "Procurement-linked signals may be stale because the latest source snapshot is older than "
        f"{max_age_days} days."
    )


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _ensure_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IngestionQualityError(f"{label} entries must be JSON objects")
    return cast(dict[str, Any], value)
