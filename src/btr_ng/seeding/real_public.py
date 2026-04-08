"""Generate deterministic real public-source seed data for BTR-NG."""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from btr_ng.registry.validator import validate_registry_dir

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
SOURCE_TOP_LEVEL_KEYS = {
    "download_url",
    "license",
    "publication_url",
    "releases",
    "retrieved_at",
    "source_id",
}
RELEASE_KEYS = {"awards", "buyer", "contracts", "date", "dateModified", "datePublished", "ocid"}
BUYER_KEYS = {"name"}
AWARD_KEYS = {"description", "id", "suppliers", "title"}
SUPPLIER_KEYS = {"identifier", "name"}
SUPPLIER_IDENTIFIER_KEYS = {"id"}
CONTRACT_KEYS = {"awardID", "description", "title"}


class RealSeedError(ValueError):
    """Raised when real public-source seeds cannot be generated safely."""


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """A curated public-source snapshot used to build committed seeds."""

    source_id: str
    publication_url: str
    download_url: str
    license: str
    retrieved_at: str
    releases: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class SeedSourceValidationResult:
    """Summary of validated seed source inputs."""

    source_count: int
    business_count: int
    evidence_reference_count: int
    dispute_count: int
    fixture_release_count: int


def validate_seed_sources(source_dir: Path) -> SeedSourceValidationResult:
    """Validate committed public-source snapshots and manifest provenance."""
    manifest = _load_json_object(source_dir / "seed_manifest.json")
    _require_string(manifest.get("generated_at"), "generated_at")
    sources = _load_sources(source_dir)
    business_specs = _require_list(manifest.get("businesses"), "businesses")
    dispute_specs = _require_list(manifest.get("disputes"), "disputes")
    fixture_spec = manifest.get("nocopo_fixture")
    business_ids: set[str] = set()
    evidence_reference_count = 0

    if not business_specs:
        raise RealSeedError("seed manifest must include at least one business")

    for business_spec_object in business_specs:
        business_spec = _require_mapping(business_spec_object, "business spec")
        btr_id = _require_string(business_spec.get("btr_id"), "btr_id")
        if btr_id in business_ids:
            raise RealSeedError(f"duplicate business btr_id in seed manifest: {btr_id}")
        business_ids.add(btr_id)
        _require_string(business_spec.get("legal_name"), "legal_name")
        _require_string(business_spec.get("slug"), "business slug")
        _require_string(business_spec.get("primary_identifier"), "primary_identifier")
        _require_string(business_spec.get("record_state"), "record_state")

        public_links = _require_list(business_spec.get("public_links"), "public_links")
        if not public_links:
            raise RealSeedError(f"{btr_id}: public_links must include at least one URL")
        for index, item in enumerate(public_links):
            _require_string(item, f"{btr_id} public_links[{index}]")

        flags = _require_list(business_spec.get("flags"), "flags")
        if not flags:
            raise RealSeedError(f"{btr_id}: flags must include at least one value")
        for index, item in enumerate(flags):
            _require_string(item, f"{btr_id} flags[{index}]")

        evidence_entries = _require_list(business_spec.get("evidence"), "evidence")
        if not evidence_entries:
            raise RealSeedError(f"{btr_id}: evidence must include at least one reference")

        for evidence_spec_object in evidence_entries:
            evidence_spec = _require_mapping(evidence_spec_object, "evidence spec")
            source_id = _require_string(evidence_spec.get("source_id"), "evidence source_id")
            source = sources.get(source_id)
            if source is None:
                raise RealSeedError(f"{btr_id}: unknown evidence source_id: {source_id}")
            release = _find_release(
                source=source,
                ocid=_require_string(evidence_spec.get("ocid"), "evidence ocid"),
            )
            _find_award(
                release=release,
                award_id=_require_string(evidence_spec.get("award_id"), "evidence award_id"),
                supplier_name=_require_string(
                    evidence_spec.get("supplier_name"),
                    "evidence supplier_name",
                ),
            )
            _require_string(evidence_spec.get("evidence_id"), "evidence_id")
            _require_string(evidence_spec.get("slug"), "evidence slug")
            _require_string(evidence_spec.get("source_kind"), "source_kind")
            evidence_reference_count += 1

    for dispute_spec_object in dispute_specs:
        dispute_spec = _require_mapping(dispute_spec_object, "dispute spec")
        dispute_business_id = _require_string(dispute_spec.get("btr_id"), "dispute btr_id")
        if dispute_business_id not in business_ids:
            raise RealSeedError(
                f"dispute references unknown business btr_id: {dispute_business_id}"
            )
        _build_dispute(dispute_spec)

    fixture_release_count = 0
    if fixture_spec is not None:
        fixture_mapping = _require_mapping(fixture_spec, "nocopo_fixture")
        _require_string(fixture_mapping.get("uri"), "fixture uri")
        source_refs = _require_list(fixture_mapping.get("source_refs"), "fixture source_refs")
        if not source_refs:
            raise RealSeedError("nocopo fixture must include at least one source ref")
        for source_ref_object in source_refs:
            source_ref = _require_mapping(source_ref_object, "fixture source_ref")
            source_id = _require_string(source_ref.get("source_id"), "fixture source_id")
            source = sources.get(source_id)
            if source is None:
                raise RealSeedError(f"unknown fixture source_id: {source_id}")
            _find_release(source, _require_string(source_ref.get("ocid"), "fixture ocid"))
            fixture_release_count += 1

    return SeedSourceValidationResult(
        source_count=len(sources),
        business_count=len(business_specs),
        evidence_reference_count=evidence_reference_count,
        dispute_count=len(dispute_specs),
        fixture_release_count=fixture_release_count,
    )


def generate_real_seed(
    source_dir: Path,
    registry_dir: Path,
    nocopo_fixture_out: Path | None = None,
) -> int:
    """Generate deterministic registry seeds from committed public-source snapshots."""
    manifest = _load_json_object(source_dir / "seed_manifest.json")
    generated_at = _require_string(manifest.get("generated_at"), "generated_at")
    sources = _load_sources(source_dir)
    business_specs = _require_list(manifest.get("businesses"), "businesses")
    dispute_specs = _require_list(manifest.get("disputes"), "disputes")
    fixture_spec = manifest.get("nocopo_fixture")
    validate_seed_sources(source_dir)

    business_documents: list[tuple[str, dict[str, object]]] = []
    evidence_documents: list[tuple[str, dict[str, object]]] = []
    dispute_documents: list[tuple[str, dict[str, object]]] = []

    for business_spec_object in business_specs:
        business_spec = _require_mapping(business_spec_object, "business spec")
        business_document, business_evidence_documents = _build_business_and_evidence(
            business_spec=business_spec,
            sources=sources,
            generated_at=generated_at,
        )
        business_slug = _require_string(business_spec.get("slug"), "business slug")
        business_documents.append((business_slug, business_document))
        for evidence_document in business_evidence_documents:
            evidence_slug = cast(str, evidence_document["_slug"])
            to_write = dict(evidence_document)
            to_write.pop("_slug", None)
            evidence_documents.append((evidence_slug, to_write))

    for dispute_spec_object in dispute_specs:
        dispute_spec = _require_mapping(dispute_spec_object, "dispute spec")
        dispute_document = _build_dispute(dispute_spec)
        dispute_slug = _require_string(dispute_spec.get("slug"), "dispute slug")
        dispute_documents.append((dispute_slug, dispute_document))

    fixture_document: dict[str, object] | None = None
    if fixture_spec is not None:
        if nocopo_fixture_out is None:
            raise RealSeedError("nocopo fixture spec exists but no output path was provided")
        fixture_document = _build_fixture(
            fixture_spec=_require_mapping(fixture_spec, "nocopo_fixture"),
            sources=sources,
        )

    businesses_dir = registry_dir / "businesses"
    evidence_dir = registry_dir / "evidence"
    disputes_dir = registry_dir / "disputes"
    for directory in (businesses_dir, evidence_dir, disputes_dir):
        directory.mkdir(parents=True, exist_ok=True)
        for existing in directory.glob("*.json"):
            existing.unlink()

    for business_slug, business_document in business_documents:
        _write_json(businesses_dir / f"{business_slug}.json", business_document)
    for evidence_slug, evidence_document in evidence_documents:
        _write_json(evidence_dir / f"{evidence_slug}.json", evidence_document)
    for dispute_slug, dispute_document in dispute_documents:
        _write_json(disputes_dir / f"{dispute_slug}.json", dispute_document)
    if fixture_document is not None and nocopo_fixture_out is not None:
        _write_json(nocopo_fixture_out, fixture_document)

    validate_registry_dir(registry_dir)
    return len(business_documents) + len(evidence_documents) + len(dispute_documents)


def _load_sources(source_dir: Path) -> dict[str, SourceSnapshot]:
    source_files = sorted(source_dir.glob("*.source.json"))
    if not source_files:
        raise RealSeedError(f"no source snapshot files found in {source_dir}")

    loaded: dict[str, SourceSnapshot] = {}
    for file_path in source_files:
        document = _load_json_object(file_path)
        _reject_extra_keys(document, SOURCE_TOP_LEVEL_KEYS, f"{file_path.name} top-level")
        _reject_sensitive_strings(document, f"{file_path.name}")

        source_id = _require_string(document.get("source_id"), "source_id")
        releases = tuple(
            _validate_release_projection(
                _require_mapping(item, f"{source_id} release"),
                source_id=source_id,
            )
            for item in _require_list(document.get("releases"), f"{source_id} releases")
        )
        loaded[source_id] = SourceSnapshot(
            source_id=source_id,
            publication_url=_require_string(
                document.get("publication_url"),
                f"{source_id} publication_url",
            ),
            download_url=_require_string(
                document.get("download_url"),
                f"{source_id} download_url",
            ),
            license=_require_string(document.get("license"), f"{source_id} license"),
            retrieved_at=_require_string(
                document.get("retrieved_at"),
                f"{source_id} retrieved_at",
            ),
            releases=releases,
        )
    return loaded


def _validate_release_projection(release: dict[str, Any], source_id: str) -> dict[str, Any]:
    _reject_extra_keys(release, RELEASE_KEYS, f"{source_id} release projection")
    _require_string(release.get("ocid"), f"{source_id} release ocid")
    buyer = _require_mapping(release.get("buyer"), f"{source_id} release buyer")
    _reject_extra_keys(buyer, BUYER_KEYS, f"{source_id} buyer projection")
    _require_string(buyer.get("name"), f"{source_id} buyer name")

    if not any(
        isinstance(release.get(field_name), str) and str(release.get(field_name)).strip()
        for field_name in ("date", "datePublished", "dateModified")
    ):
        raise RealSeedError(f"{source_id} release must include a date field")

    awards = _require_list(release.get("awards"), f"{source_id} release awards")
    if not awards:
        raise RealSeedError(f"{source_id} release awards must include at least one award")
    for award_object in awards:
        award = _require_mapping(award_object, f"{source_id} award")
        _reject_extra_keys(award, AWARD_KEYS, f"{source_id} award projection")
        _require_string(award.get("id"), f"{source_id} award id")
        suppliers = _require_list(award.get("suppliers"), f"{source_id} award suppliers")
        if not suppliers:
            raise RealSeedError(f"{source_id} award suppliers must include at least one supplier")
        for supplier_object in suppliers:
            supplier = _require_mapping(supplier_object, f"{source_id} supplier")
            _reject_extra_keys(supplier, SUPPLIER_KEYS, f"{source_id} supplier projection")
            _require_string(supplier.get("name"), f"{source_id} supplier name")
            identifier = supplier.get("identifier")
            if identifier is not None:
                identifier_mapping = _require_mapping(
                    identifier,
                    f"{source_id} supplier identifier",
                )
                _reject_extra_keys(
                    identifier_mapping,
                    SUPPLIER_IDENTIFIER_KEYS,
                    f"{source_id} supplier identifier projection",
                )
                _require_string(identifier_mapping.get("id"), f"{source_id} supplier identifier id")

    contracts = release.get("contracts", [])
    if contracts is not None:
        contract_items = _require_list(contracts, f"{source_id} release contracts")
        for contract_object in contract_items:
            contract = _require_mapping(contract_object, f"{source_id} contract")
            _reject_extra_keys(contract, CONTRACT_KEYS, f"{source_id} contract projection")
            _require_string(contract.get("awardID"), f"{source_id} contract awardID")
    return release


def _build_business_and_evidence(
    business_spec: dict[str, Any],
    sources: dict[str, SourceSnapshot],
    generated_at: str,
) -> tuple[dict[str, object], tuple[dict[str, object], ...]]:
    btr_id = _require_string(business_spec.get("btr_id"), "btr_id")
    legal_name = _require_string(business_spec.get("legal_name"), "legal_name")
    evidence_entries = _require_list(business_spec.get("evidence"), "evidence")
    evidence_documents: list[dict[str, object]] = []
    evidence_refs: list[str] = []

    for evidence_spec_object in evidence_entries:
        evidence_spec = _require_mapping(evidence_spec_object, "evidence spec")
        evidence_document = _build_evidence_document(
            btr_id=btr_id,
            legal_name=legal_name,
            evidence_spec=evidence_spec,
            sources=sources,
            generated_at=generated_at,
        )
        evidence_documents.append(evidence_document)
        evidence_refs.append(cast(str, evidence_document["evidence_id"]))

    business_document: dict[str, object] = {
        "btr_id": btr_id,
        "legal_name": legal_name,
        "jurisdiction": "NG",
        "identifiers": {
            "primary": _require_string(
                business_spec.get("primary_identifier"),
                "primary_identifier",
            ),
        },
        "public_links": [
            _require_string(item, "public link")
            for item in _require_list(business_spec.get("public_links"), "public_links")
        ],
        "evidence_refs": evidence_refs,
        "derived_signals": {
            "procurement_activity": True,
            "manual_verification": False,
            "flags": [
                _require_string(item, "flag")
                for item in _require_list(business_spec.get("flags"), "flags")
            ],
        },
        "record_state": _require_string(business_spec.get("record_state"), "record_state"),
        "updated_at": generated_at,
    }
    trading_name = business_spec.get("trading_name")
    if isinstance(trading_name, str) and trading_name.strip():
        business_document["trading_name"] = trading_name.strip()

    secondary_identifiers = business_spec.get("secondary_identifiers")
    if isinstance(secondary_identifiers, list) and secondary_identifiers:
        cast(dict[str, object], business_document["identifiers"])["secondary"] = [
            _require_string(item, "secondary identifier")
            for item in secondary_identifiers
        ]

    return business_document, tuple(evidence_documents)


def _build_evidence_document(
    btr_id: str,
    legal_name: str,
    evidence_spec: dict[str, Any],
    sources: dict[str, SourceSnapshot],
    generated_at: str,
) -> dict[str, object]:
    source_id = _require_string(evidence_spec.get("source_id"), "evidence source_id")
    source = sources.get(source_id)
    if source is None:
        raise RealSeedError(f"unknown source_id in evidence spec: {source_id}")

    release = _find_release(
        source=source,
        ocid=_require_string(evidence_spec.get("ocid"), "evidence ocid"),
    )
    award_id = _require_string(evidence_spec.get("award_id"), "evidence award_id")
    supplier_name = _require_string(
        evidence_spec.get("supplier_name"),
        "evidence supplier_name",
    )
    award = _find_award(release, award_id, supplier_name)
    buyer = _require_mapping(release.get("buyer"), "release buyer")
    buyer_name = _require_string(buyer.get("name"), "buyer name")
    observed_at = _release_date(release)
    summary_context = _summary_context(release, award)
    source_kind = _require_string(evidence_spec.get("source_kind"), "source_kind")
    evidence_id = _require_string(evidence_spec.get("evidence_id"), "evidence_id")
    slug = _require_string(evidence_spec.get("slug"), "evidence slug")

    payload_for_hash = {
        "source_id": source.source_id,
        "ocid": release.get("ocid"),
        "award_id": award_id,
        "buyer_name": buyer_name,
        "supplier_name": html.unescape(supplier_name),
        "summary_context": summary_context,
    }
    sha256 = hashlib.sha256(
        json.dumps(payload_for_hash, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "_slug": slug,
        "evidence_id": evidence_id,
        "source_url": source.publication_url,
        "source_type": "procurement_notice",
        "observed_at": observed_at,
        "recorded_at": generated_at,
        "sha256": sha256,
        "access": "public_reference",
        "summary": (
            "Published procurement record derived from published procurement data. "
            f"{html.unescape(legal_name)} appears in {buyer_name} procurement record "
            f"{release['ocid']} for {summary_context}."
        ),
        "related_businesses": [btr_id],
        "tags": ["procurement", source_kind],
    }


def _build_dispute(dispute_spec: dict[str, Any]) -> dict[str, object]:
    return {
        "case_id": _require_string(dispute_spec.get("case_id"), "case_id"),
        "btr_id": _require_string(dispute_spec.get("btr_id"), "btr_id"),
        "review_type": _require_string(dispute_spec.get("review_type"), "review_type"),
        "state": _require_string(dispute_spec.get("state"), "state"),
        "redacted_summary": _require_string(
            dispute_spec.get("redacted_summary"),
            "redacted_summary",
        ),
        "evidence_pack_refs": [
            _require_string(item, "evidence_pack_ref")
            for item in _require_list(dispute_spec.get("evidence_pack_refs"), "evidence_pack_refs")
        ],
        "opened_at": _require_string(dispute_spec.get("opened_at"), "opened_at"),
        "updated_at": _require_string(dispute_spec.get("updated_at"), "updated_at"),
    }


def _build_fixture(
    fixture_spec: dict[str, Any],
    sources: dict[str, SourceSnapshot],
) -> dict[str, object]:
    releases: list[dict[str, object]] = []
    source_refs = _require_list(fixture_spec.get("source_refs"), "fixture source_refs")
    retrieval_times: list[datetime] = []
    for source_ref_object in source_refs:
        source_ref = _require_mapping(source_ref_object, "fixture source_ref")
        source_id = _require_string(source_ref.get("source_id"), "fixture source_id")
        source = sources.get(source_id)
        if source is None:
            raise RealSeedError(f"unknown fixture source_id: {source_id}")
        release = _find_release(source, _require_string(source_ref.get("ocid"), "fixture ocid"))
        releases.append(release)
        retrieval_times.append(_parse_datetime(source.retrieved_at))

    if not retrieval_times:
        raise RealSeedError("fixture must include at least one source ref")
    published_date = max(retrieval_times)
    return {
        "uri": _require_string(fixture_spec.get("uri"), "fixture uri"),
        "publishedDate": published_date.isoformat().replace("+00:00", "Z"),
        "version": "1.1",
        "releases": releases,
    }


def _find_release(source: SourceSnapshot, ocid: str) -> dict[str, Any]:
    for release in source.releases:
        if str(release.get("ocid")) == ocid:
            return release
    raise RealSeedError(f"{source.source_id}: missing release for ocid {ocid}")


def _find_award(
    release: dict[str, Any],
    award_id: str,
    supplier_name: str,
) -> dict[str, Any]:
    awards = _require_list(release.get("awards"), "release awards")
    normalized_supplier_name = html.unescape(supplier_name).strip().lower()
    for award_object in awards:
        award = _require_mapping(award_object, "award")
        if str(award.get("id")) != award_id:
            continue
        suppliers = _require_list(award.get("suppliers"), "award suppliers")
        for supplier_object in suppliers:
            supplier = _require_mapping(supplier_object, "supplier")
            candidate = html.unescape(str(supplier.get("name", ""))).strip().lower()
            if candidate == normalized_supplier_name:
                return award
    raise RealSeedError(
        f"missing award {award_id} for supplier {supplier_name} in release {release.get('ocid')}"
    )


def _summary_context(release: dict[str, Any], award: dict[str, Any]) -> str:
    contracts = release.get("contracts")
    if isinstance(contracts, list):
        for contract_object in contracts:
            contract = _require_mapping(contract_object, "contract")
            if str(contract.get("awardID", "")) == str(award.get("id", "")):
                title = str(contract.get("title", "")).strip()
                description = str(contract.get("description", "")).strip()
                if title:
                    return title
                if description:
                    return description
    title = str(award.get("title", "")).strip()
    description = str(award.get("description", "")).strip()
    if title:
        return title
    if description:
        return description
    return f"award {award.get('id')}"


def _release_date(release: dict[str, Any]) -> str:
    return _release_date_object(release).isoformat().replace("+00:00", "Z")


def _release_date_object(release: dict[str, Any]) -> datetime:
    candidates = []
    for field_name in ("date", "datePublished", "dateModified"):
        value = release.get(field_name)
        if isinstance(value, str) and value.strip():
            candidates.append(_parse_datetime(value))
    if not candidates:
        raise RealSeedError(f"release {release.get('ocid')} is missing a date field")
    return max(candidates)


def _reject_extra_keys(value: dict[str, Any], allowed_keys: set[str], field_name: str) -> None:
    extra_keys = sorted(set(value) - allowed_keys)
    if extra_keys:
        raise RealSeedError(
            f"{field_name} contains unsupported fields: {', '.join(extra_keys)}"
        )


def _reject_sensitive_strings(value: Any, field_name: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_sensitive_strings(item, f"{field_name}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_sensitive_strings(item, f"{field_name}[{index}]")
        return
    if not isinstance(value, str):
        return
    email_match = EMAIL_PATTERN.search(value)
    if email_match is not None:
        raise RealSeedError(
            f"{field_name} contains a disallowed email-like string: {email_match.group(0)}"
        )
    phone_match = PHONE_PATTERN.search(value)
    if phone_match is not None:
        digits_only = re.sub(r"\D", "", phone_match.group(0))
        lowered_field_name = field_name.lower()
        if (
            len(digits_only) >= 10
            and "ocid" not in lowered_field_name
            and "awardid" not in lowered_field_name
            and not lowered_field_name.endswith(".id")
        ):
            raise RealSeedError(
                f"{field_name} contains a disallowed phone-like string: {phone_match.group(0)}"
            )


def _write_json(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RealSeedError(f"{path}: invalid JSON: {error.msg}") from error
    if not isinstance(document, dict):
        raise RealSeedError(f"{path}: expected a top-level JSON object")
    return cast(dict[str, Any], document)


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RealSeedError(f"{field_name} must be an object")
    return cast(dict[str, Any], value)


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise RealSeedError(f"{field_name} must be a list")
    return list(value)


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealSeedError(f"{field_name} must be a non-empty string")
    return value.strip()


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
