"""NOCOPO/OCDS ingestion for derived procurement metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast


class IngestionError(ValueError):
    """Raised when a procurement fixture cannot be ingested safely."""


@dataclass(slots=True)
class SupplierAggregate:
    """Aggregated procurement metrics for one matched supplier."""

    btr_id: str
    supplier_name: str
    supplier_identifier: str
    matched_on: str
    buyers: set[str] = field(default_factory=set)
    ocids: set[str] = field(default_factory=set)
    contracts_count: int = 0
    awards_count: int = 0
    last_seen: datetime | None = None


def ingest_nocopo_fixture(
    input_path: Path,
    registry_dir: Path,
    out_dir: Path,
) -> int:
    """Parse an OCDS fixture and emit matched supplier summaries."""
    package = _load_package(input_path)
    business_index = _load_business_index(registry_dir)
    releases = _load_releases(package)
    if not releases:
        raise IngestionError("fixture does not contain any OCDS releases")

    aggregates: dict[str, SupplierAggregate] = {}
    distinct_suppliers: set[str] = set()

    for release in releases:
        ocid = str(release.get("ocid", "")).strip()
        if not ocid:
            raise IngestionError("every release must include an ocid")

        buyer_name = _buyer_name(release)
        release_dates = _release_dates(release)
        awards = release.get("awards", [])
        contracts = release.get("contracts", [])
        if not isinstance(awards, list):
            raise IngestionError(f"{ocid}: awards must be a list")
        if not isinstance(contracts, list):
            raise IngestionError(f"{ocid}: contracts must be a list")

        award_suppliers: dict[str, tuple[tuple[str, str], ...]] = {}
        for award in awards:
            if not isinstance(award, dict):
                raise IngestionError(f"{ocid}: award entries must be objects")
            award_id = str(award.get("id", "")).strip()
            extracted_suppliers = _extract_suppliers(award, ocid)
            if award_id:
                award_suppliers[_normalize(award_id)] = extracted_suppliers
            for supplier_name, supplier_identifier in extracted_suppliers:
                distinct_suppliers.add(_normalize(supplier_identifier or supplier_name))
                match = _match_business(business_index, supplier_name, supplier_identifier)
                if match is None:
                    continue
                aggregate = aggregates.setdefault(
                    match[0],
                    SupplierAggregate(
                        btr_id=match[0],
                        supplier_name=supplier_name,
                        supplier_identifier=supplier_identifier,
                        matched_on=match[1],
                    ),
                )
                aggregate.awards_count += 1
                aggregate.buyers.add(buyer_name)
                aggregate.ocids.add(ocid)
                _update_last_seen(aggregate, release_dates)
        for contract in contracts:
            if not isinstance(contract, dict):
                raise IngestionError(f"{ocid}: contract entries must be objects")
            award_id = str(contract.get("awardID", "")).strip()
            contract_suppliers = _suppliers_for_contract(
                contract=contract,
                award_suppliers=award_suppliers,
                ocid=ocid,
                award_id=award_id,
            )
            for supplier_name, supplier_identifier in contract_suppliers:
                distinct_suppliers.add(_normalize(supplier_identifier or supplier_name))
                match = _match_business(business_index, supplier_name, supplier_identifier)
                if match is None:
                    continue
                aggregate = aggregates.setdefault(
                    match[0],
                    SupplierAggregate(
                        btr_id=match[0],
                        supplier_name=supplier_name,
                        supplier_identifier=supplier_identifier,
                        matched_on=match[1],
                    ),
                )
                aggregate.contracts_count += 1
                aggregate.buyers.add(buyer_name)
                aggregate.ocids.add(ocid)
                _update_last_seen(aggregate, release_dates)

    generated_at = max(_release_dates(release) for release in releases)
    out_dir.mkdir(parents=True, exist_ok=True)
    for aggregate in sorted(aggregates.values(), key=lambda item: item.btr_id):
        document = {
            "source": "nocopo",
            "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
            "source_input": input_path.name,
            "btr_id": aggregate.btr_id,
            "supplier_name": aggregate.supplier_name,
            "supplier_identifier": aggregate.supplier_identifier,
            "matched_on": aggregate.matched_on,
            "supplier_count": len(distinct_suppliers),
            "awards_count": aggregate.awards_count,
            "contracts_count": aggregate.contracts_count,
            "buyer_diversity_count": len(aggregate.buyers),
            "buyers": sorted(aggregate.buyers),
            "ocids": sorted(aggregate.ocids),
            "last_seen": (
                aggregate.last_seen.isoformat().replace("+00:00", "Z")
                if aggregate.last_seen is not None
                else generated_at.isoformat().replace("+00:00", "Z")
            ),
        }
        output_path = out_dir / f"{aggregate.btr_id}.json"
        output_path.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return len(aggregates)


def _load_package(input_path: Path) -> dict[str, Any]:
    if not input_path.exists():
        raise IngestionError(f"input fixture does not exist: {input_path}")
    try:
        package = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise IngestionError(f"{input_path}: invalid JSON: {error.msg}") from error
    if not isinstance(package, dict):
        raise IngestionError("top-level OCDS fixture must be a JSON object")
    return cast(dict[str, Any], package)


def _load_releases(package: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    releases = package.get("releases")
    if isinstance(releases, list):
        return tuple(_ensure_object(release, "release") for release in releases)

    records = package.get("records")
    if isinstance(records, list):
        compiled: list[dict[str, Any]] = []
        for record in records:
            record_object = _ensure_object(record, "record")
            compiled_release = record_object.get("compiledRelease")
            compiled.append(_ensure_object(compiled_release, "compiledRelease"))
        return tuple(compiled)

    raise IngestionError("fixture must contain either a 'releases' list or a 'records' list")


def _load_business_index(registry_dir: Path) -> dict[str, tuple[str, str]]:
    businesses_dir = registry_dir / "businesses"
    if not businesses_dir.exists():
        raise IngestionError(f"registry businesses directory does not exist: {businesses_dir}")

    index: dict[str, tuple[str, str]] = {}
    for file_path in sorted(businesses_dir.glob("*.json")):
        business = _load_package(file_path)
        btr_id = str(business["btr_id"])
        index[_normalize(str(business["legal_name"]))] = (btr_id, "legal_name")
        trading_name = business.get("trading_name")
        if isinstance(trading_name, str):
            index[_normalize(trading_name)] = (btr_id, "trading_name")
        identifiers = business.get("identifiers", {})
        if isinstance(identifiers, dict):
            primary = identifiers.get("primary")
            if isinstance(primary, str):
                index[_normalize(primary)] = (btr_id, "primary_identifier")
            secondary = identifiers.get("secondary", [])
            if isinstance(secondary, list):
                for value in secondary:
                    index[_normalize(str(value))] = (btr_id, "secondary_identifier")
    return index


def _match_business(
    business_index: dict[str, tuple[str, str]],
    supplier_name: str,
    supplier_identifier: str,
) -> tuple[str, str] | None:
    identifier_key = _normalize(supplier_identifier)
    if identifier_key and identifier_key in business_index:
        return business_index[identifier_key]
    name_key = _normalize(supplier_name)
    return business_index.get(name_key)


def _extract_suppliers(award: dict[str, Any], ocid: str) -> tuple[tuple[str, str], ...]:
    suppliers = award.get("suppliers", [])
    if not isinstance(suppliers, list):
        raise IngestionError(f"{ocid}: award suppliers must be a list")
    extracted: list[tuple[str, str]] = []
    for supplier in suppliers:
        supplier_object = _ensure_object(supplier, "supplier")
        supplier_name = str(supplier_object.get("name", "")).strip()
        if not supplier_name:
            raise IngestionError(f"{ocid}: supplier name is required")
        supplier_identifier = _supplier_identifier(supplier_object)
        extracted.append((supplier_name, supplier_identifier))
    return tuple(extracted)


def _supplier_identifier(supplier: dict[str, Any]) -> str:
    identifier = supplier.get("identifier")
    if isinstance(identifier, dict):
        return str(identifier.get("id", "")).strip()
    return ""


def _suppliers_for_contract(
    contract: dict[str, Any],
    award_suppliers: dict[str, tuple[tuple[str, str], ...]],
    ocid: str,
    award_id: str,
) -> tuple[tuple[str, str], ...]:
    suppliers = contract.get("suppliers")
    if isinstance(suppliers, list):
        return tuple(_extract_suppliers({"suppliers": suppliers}, ocid))

    if award_id:
        suppliers_for_award = award_suppliers.get(_normalize(award_id))
        if suppliers_for_award is not None:
            return suppliers_for_award

    return ()


def _buyer_name(release: dict[str, Any]) -> str:
    buyer = release.get("buyer", {})
    if not isinstance(buyer, dict):
        raise IngestionError("release buyer must be an object")
    buyer_name = str(buyer.get("name", "")).strip()
    if not buyer_name:
        raise IngestionError("release buyer name is required")
    return buyer_name


def _release_dates(release: dict[str, Any]) -> datetime:
    candidates: list[datetime] = []
    for field_name in ("date", "datePublished", "dateModified"):
        value = release.get(field_name)
        if isinstance(value, str) and value.strip():
            candidates.append(_parse_datetime(value))
    if not candidates:
        raise IngestionError("release must include at least one date field")
    return max(candidates)


def _update_last_seen(aggregate: SupplierAggregate, observed_at: datetime) -> None:
    if aggregate.last_seen is None or observed_at > aggregate.last_seen:
        aggregate.last_seen = observed_at


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _ensure_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IngestionError(f"{label} entries must be JSON objects")
    return cast(dict[str, Any], value)
