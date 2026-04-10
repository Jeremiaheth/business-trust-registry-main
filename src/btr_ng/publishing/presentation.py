"""Presentation-oriented view models for the public API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast


def build_directory_filters(
    index_items: list[dict[str, object]],
) -> dict[str, object]:
    """Build UI filter metadata for the directory experience."""
    evidence_counts = [
        cast(int, item["evidence_count"])
        for item in index_items
        if isinstance(item.get("evidence_count"), int)
    ]
    scores = [
        float(cast(int | float, item["score"]))
        for item in index_items
        if isinstance(item.get("score"), int | float)
    ]
    confidence = [
        float(cast(int | float, item["confidence"]))
        for item in index_items
        if isinstance(item.get("confidence"), int | float)
    ]
    display_states = sorted(
        {str(item.get("display_state", "normal")) for item in index_items}
    )
    confidence_bands = sorted(
        {str(item.get("confidence_band", "limited")) for item in index_items}
    )
    return {
        "verified_status": {
            "enabled": True,
            "label": "Verification status",
            "options": display_states,
        },
        "trust_score_range": {
            "enabled": True,
            "label": "Trust score range",
            "min": min(scores) if scores else 0.0,
            "max": max(scores) if scores else 1.0,
        },
        "confidence_level": {
            "enabled": True,
            "label": "Confidence level",
            "options": confidence_bands,
            "min": min(confidence) if confidence else 0.0,
            "max": max(confidence) if confidence else 1.0,
        },
        "evidence_count": {
            "enabled": True,
            "label": "Evidence count",
            "min": min(evidence_counts) if evidence_counts else 0,
            "max": max(evidence_counts) if evidence_counts else 0,
        },
        "procurement_activity": {
            "enabled": True,
            "label": "Procurement-linked evidence",
            "options": ["available", "not_available"],
        },
        "open_review": {
            "enabled": True,
            "label": "Review state",
            "options": ["under_review", "not_under_review"],
        },
        "sector": {
            "enabled": False,
            "label": "Sector",
            "note": "Not yet available in public beta.",
        },
        "location": {
            "enabled": False,
            "label": "Location",
            "note": "Not yet available in public beta.",
        },
    }


def build_search_entry(
    business: dict[str, object],
    score: dict[str, object],
    evidence: list[dict[str, object]],
) -> dict[str, object]:
    """Build a client-facing search entry."""
    identifiers = cast(dict[str, object], business.get("identifiers", {}))
    procurement_active = bool(
        cast(dict[str, object], business.get("derived_signals", {})).get(
            "procurement_activity", False
        )
    )
    dispute_open = str(score.get("display_state", "normal")) == "under_review"
    tags = _collect_tags(business, evidence)
    terms = {
        str(business["btr_id"]).lower(),
        str(business["legal_name"]).lower(),
        str(business["jurisdiction"]).lower(),
    }
    trading_name = business.get("trading_name")
    if isinstance(trading_name, str) and trading_name:
        terms.add(trading_name.lower())
    primary_identifier = identifiers.get("primary")
    if isinstance(primary_identifier, str):
        terms.add(primary_identifier.lower())
    secondary_identifiers = identifiers.get("secondary", [])
    if isinstance(secondary_identifiers, list):
        for value in secondary_identifiers:
            terms.add(str(value).lower())
    for tag in tags:
        terms.add(tag.lower())

    summary = str(score.get("public_note", "Based on available verified evidence."))
    return {
        "btr_id": str(business["btr_id"]),
        "display_name": (
            str(trading_name)
            if isinstance(trading_name, str) and trading_name
            else str(business["legal_name"])
        ),
        "legal_name": str(business["legal_name"]),
        "trading_name": str(trading_name) if isinstance(trading_name, str) else "",
        "jurisdiction": str(business["jurisdiction"]),
        "display_state": str(score["display_state"]),
        "score": score["score"],
        "confidence": score["confidence"],
        "confidence_band": confidence_band(_as_float(score["confidence"])),
        "band": score["band"],
        "summary": summary,
        "evidence_count": len(evidence),
        "procurement_activity": procurement_active,
        "open_review": dispute_open,
        "badges": build_badges(score=score, evidence=evidence, business=business),
        "tags": sorted(tags),
        "terms": sorted(terms),
        "filters": {
            "verified_status": str(score["display_state"]),
            "confidence_level": confidence_band(_as_float(score["confidence"])),
            "procurement_activity": "available" if procurement_active else "not_available",
            "open_review": "under_review" if dispute_open else "not_under_review",
        },
    }


def build_business_presentation(
    business: dict[str, object],
    score: dict[str, object],
    evidence: list[dict[str, object]],
    disputes: list[dict[str, object]],
    derived_records: list[dict[str, object]],
) -> dict[str, object]:
    """Build presentation-specific fields for a business profile."""
    business_id = str(business["btr_id"])
    trading_name = business.get("trading_name")
    display_name = (
        str(trading_name)
        if isinstance(trading_name, str) and trading_name
        else str(business["legal_name"])
    )
    timeline = build_timeline(
        business=business,
        score=score,
        evidence=evidence,
        disputes=disputes,
        derived_records=derived_records,
    )
    procurement_panel = build_procurement_panel(derived_records)
    report_route = f"/reports/{business_id}"
    return {
        "display_name": display_name,
        "headline_summary": _headline_summary(score, evidence),
        "trust_status_label": banner_label(str(score["display_state"])),
        "decision_support_note": (
            "Decision-support only. BTR-NG publishes an evidence-based view and is not a "
            "government certification."
        ),
        "badges": build_badges(score=score, evidence=evidence, business=business),
        "confidence_band": confidence_band(_as_float(score["confidence"])),
        "dimension_breakdown": build_dimension_breakdown(score),
        "timeline": timeline,
        "verification_panels": {
            "identity": {
                "availability": "available",
                "label": "Identity verification",
                "status": "evidence_backed",
                "primary_identifier": cast(dict[str, object], business.get("identifiers", {})).get(
                    "primary", ""
                ),
                "public_links": business.get("public_links", []),
                "note": "Identity coverage is derived from public identifiers and linked evidence.",
            },
            "cac": unavailable_beta_panel(
                "CAC verification",
                "CAC integration is not yet available in the public beta.",
            ),
            "psc": unavailable_beta_panel(
                "PSC disclosure presence",
                "PSC disclosure integration is not yet available in the public beta.",
            ),
            "procurement": procurement_panel,
            "evidence_quality": {
                "availability": "available",
                "label": "Evidence quality",
                "status": "available",
                "evidence_count": len(evidence),
                "source_types": sorted(
                    {str(item.get("source_type", "public_reference")) for item in evidence}
                ),
                "note": (
                    "Evidence quality reflects the completeness of public-source "
                    "references in the profile."
                ),
            },
        },
        "report": {
            "availability": "html_only",
            "route": report_route,
            "api_path": f"/api/v1/reports/{business_id}.json",
            "title": f"{display_name} trust report",
            "note": (
                "HTML report only in public beta. No signed artifact is published "
                "in this phase."
            ),
        },
    }


def build_report_document(
    business: dict[str, object],
    score: dict[str, object],
    evidence: list[dict[str, object]],
    disputes: list[dict[str, object]],
    derived_records: list[dict[str, object]],
    generated_at: str,
) -> dict[str, object]:
    """Build the dedicated trust report document."""
    presentation = build_business_presentation(
        business=business,
        score=score,
        evidence=evidence,
        disputes=disputes,
        derived_records=derived_records,
    )
    return {
        "btr_id": str(business["btr_id"]),
        "generated_at": generated_at,
        "display_name": presentation["display_name"],
        "title": cast(dict[str, object], presentation["report"])["title"],
        "decision_support_note": presentation["decision_support_note"],
        "headline_summary": presentation["headline_summary"],
        "badges": presentation["badges"],
        "scorecard": {
            "score": score["score"],
            "confidence": score["confidence"],
            "confidence_band": presentation["confidence_band"],
            "band": score["band"],
            "status": score["status"],
            "display_state": score["display_state"],
            "verification_timestamp": score["verification_timestamp"],
        },
        "dimension_breakdown": presentation["dimension_breakdown"],
        "timeline": presentation["timeline"],
        "verification_panels": presentation["verification_panels"],
        "evidence": [
            {
                "evidence_id": item["evidence_id"],
                "summary": item["summary"],
                "observed_at": item["observed_at"],
                "source_url": item["source_url"],
                "tags": item.get("tags", []),
            }
            for item in evidence
        ],
        "disputes": [
            {
                "case_id": item["case_id"],
                "state": item["state"],
                "redacted_summary": item["redacted_summary"],
                "updated_at": item["updated_at"],
            }
            for item in disputes
        ],
    }


def build_timeline(
    *,
    business: dict[str, object],
    score: dict[str, object],
    evidence: list[dict[str, object]],
    disputes: list[dict[str, object]],
    derived_records: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Build a descending timeline of public verification events."""
    timeline: list[dict[str, object]] = [
        {
            "timestamp": str(score["verification_timestamp"]),
            "type": "score_refresh",
            "label": "Trust score refreshed",
            "status": str(score["display_state"]),
            "description": str(score["public_note"]),
        },
        {
            "timestamp": str(business["updated_at"]),
            "type": "profile_update",
            "label": "Profile record updated",
            "status": str(business["record_state"]),
            "description": "Public profile metadata was refreshed from the validated registry.",
        },
    ]
    for item in evidence:
        timeline.append(
            {
                "timestamp": str(item["observed_at"]),
                "type": "evidence_reference",
                "label": str(item["evidence_id"]),
                "status": str(item["source_type"]),
                "description": str(item["summary"]),
                "source_url": str(item["source_url"]),
            }
        )
    for item in disputes:
        timeline.append(
            {
                "timestamp": str(item["updated_at"]),
                "type": "fact_correction",
                "label": str(item["case_id"]),
                "status": str(item["state"]),
                "description": str(item["redacted_summary"]),
            }
        )
    for record in derived_records:
        document = cast(dict[str, object], record.get("document", {}))
        generated_at = document.get("generated_at")
        if isinstance(generated_at, str):
            timeline.append(
                {
                    "timestamp": generated_at,
                    "type": "derived_procurement",
                    "label": str(record.get("path", "derived-record")),
                    "status": "derived",
                    "description": (
                        "Procurement-linked supplier metrics were refreshed from "
                        "derived public data."
                    ),
                }
            )
    timeline.sort(key=lambda item: _parse_datetime(str(item["timestamp"])), reverse=True)
    return timeline


def build_badges(
    *,
    score: dict[str, object],
    evidence: list[dict[str, object]],
    business: dict[str, object],
) -> list[dict[str, str]]:
    """Build badge labels for the UI."""
    badges = [
        {
            "kind": "state",
            "label": banner_label(str(score["display_state"])),
            "tone": str(score["display_state"]),
        },
        {
            "kind": "band",
            "label": f"{str(score['band']).title()} trust band",
            "tone": str(score["band"]),
        },
        {
            "kind": "confidence",
            "label": f"{confidence_band(_as_float(score['confidence'])).title()} confidence",
            "tone": confidence_band(_as_float(score["confidence"])),
        },
    ]
    if bool(
        cast(dict[str, object], business.get("derived_signals", {})).get(
            "procurement_activity", False
        )
    ):
        badges.append(
            {
                "kind": "procurement",
                "label": "Procurement-linked evidence",
                "tone": "positive",
            }
        )
    if evidence:
        badges.append(
            {
                "kind": "evidence",
                "label": f"{len(evidence)} evidence reference{'s' if len(evidence) != 1 else ''}",
                "tone": "neutral",
            }
        )
    return badges


def build_index_entry(
    business: dict[str, object],
    score: dict[str, object],
    evidence: list[dict[str, object]],
) -> dict[str, object]:
    """Build the index card shape used by the homepage and directory."""
    procurement_active = bool(
        cast(dict[str, object], business.get("derived_signals", {})).get(
            "procurement_activity", False
        )
    )
    return {
        "btr_id": str(business["btr_id"]),
        "legal_name": str(business["legal_name"]),
        "trading_name": str(business.get("trading_name", "")),
        "jurisdiction": str(business["jurisdiction"]),
        "record_state": str(business["record_state"]),
        "score": score["score"],
        "confidence": score["confidence"],
        "confidence_band": confidence_band(_as_float(score["confidence"])),
        "band": score["band"],
        "status": score["status"],
        "display_state": score["display_state"],
        "public_note": score["public_note"],
        "verification_timestamp": score["verification_timestamp"],
        "evidence_count": len(evidence),
        "procurement_activity": procurement_active,
        "badges": build_badges(score=score, evidence=evidence, business=business),
    }


def build_procurement_panel(derived_records: list[dict[str, object]]) -> dict[str, object]:
    """Build the procurement panel from derived records."""
    procurement_documents = [
        cast(dict[str, object], item["document"])
        for item in derived_records
        if isinstance(item.get("document"), dict)
        and cast(dict[str, object], item["document"]).get("source") == "nocopo"
    ]
    if not procurement_documents:
        return unavailable_beta_panel(
            "Procurement / NOCOPO signals",
            "No procurement-derived summary is attached to this public profile yet.",
        )
    document = procurement_documents[0]
    return {
        "availability": "available",
        "label": "Procurement / NOCOPO signals",
        "status": "available",
        "awards_count": _as_int(document.get("awards_count", 0)),
        "buyers": document.get("buyers", []),
        "buyer_diversity_count": _as_int(document.get("buyer_diversity_count", 0)),
        "last_seen": document.get("last_seen", ""),
        "note": (
            "Procurement-linked signals are derived from published procurement "
            "data and remain complementary evidence."
        ),
    }


def build_dimension_breakdown(score: dict[str, object]) -> list[dict[str, object]]:
    """Map the current score dimensions into the public trust portal breakdown."""
    source_dimensions = {
        str(item["name"]): item
        for item in cast(list[dict[str, object]], score.get("dimensions", []))
    }
    mappings = (
        ("identity", "identity", "Identity", "Public identifier and profile continuity."),
        (
            "compliance",
            "evidence_quality",
            "Compliance",
            "Evidence breadth and reference quality.",
        ),
        (
            "performance",
            "procurement_presence",
            "Performance",
            "Observed procurement-linked delivery signals.",
        ),
        (
            "responsiveness",
            "manual_verification",
            "Responsiveness",
            "Manual review support and operator responsiveness.",
        ),
    )
    breakdown: list[dict[str, object]] = []
    for key, source_name, label, note in mappings:
        source = source_dimensions.get(source_name)
        if source is None:
            breakdown.append(unavailable_dimension(key, label, note))
            continue
        breakdown.append(
            {
                "key": key,
                "label": label,
                "availability": "available",
                "score": source["score"],
                "confidence": source["confidence"],
                "weighted_score": source["weighted_score"],
                "source_dimension": source_name,
                "note": note,
            }
        )
    breakdown.append(
        unavailable_dimension(
            "market_feedback",
            "Market feedback",
            "Market feedback integration is not yet available in the public beta.",
        )
    )
    return breakdown


def unavailable_beta_panel(label: str, note: str) -> dict[str, object]:
    """Return a standard unavailable beta panel."""
    return {
        "availability": "unavailable_beta",
        "label": label,
        "status": "unavailable_beta",
        "note": note,
    }


def unavailable_dimension(key: str, label: str, note: str) -> dict[str, object]:
    """Return a standard unavailable dimension entry."""
    return {
        "key": key,
        "label": label,
        "availability": "unavailable_beta",
        "score": None,
        "confidence": None,
        "weighted_score": None,
        "source_dimension": None,
        "note": note,
    }


def banner_label(display_state: str) -> str:
    """Return a human-readable status label."""
    labels = {
        "normal": "Published profile",
        "insufficient_evidence": "Insufficient evidence",
        "under_review": "Under review",
        "maintenance": "Maintenance mode",
    }
    return labels.get(display_state, "Profile status")


def confidence_band(confidence: float) -> str:
    """Map a numeric confidence value to a public label."""
    if confidence >= 0.65:
        return "strong"
    if confidence >= 0.4:
        return "moderate"
    return "limited"


def _headline_summary(score: dict[str, object], evidence: list[dict[str, object]]) -> str:
    state = str(score["display_state"])
    if state == "under_review":
        return (
            "A public fact-correction case is open, so the profile remains visible "
            "with explicit review status."
        )
    if state == "insufficient_evidence":
        return (
            "Public evidence remains too thin for a stable publication-grade trust "
            "interpretation."
        )
    return (
        f"This profile is based on {len(evidence)} public evidence reference"
        f"{'s' if len(evidence) != 1 else ''} and a deterministic score snapshot."
    )


def _collect_tags(
    business: dict[str, object],
    evidence: list[dict[str, object]],
) -> set[str]:
    tags: set[str] = set()
    derived_signals = cast(dict[str, object], business.get("derived_signals", {}))
    flags = derived_signals.get("flags", [])
    if isinstance(flags, list):
        for flag in flags:
            tags.add(str(flag))
    for evidence_item in evidence:
        evidence_tags = evidence_item.get("tags", [])
        if isinstance(evidence_tags, list):
            for tag in evidence_tags:
                tags.add(str(tag))
    return tags


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_float(value: object) -> float:
    return float(cast(int | float | str, value))


def _as_int(value: object) -> int:
    return int(cast(int | str, value))
