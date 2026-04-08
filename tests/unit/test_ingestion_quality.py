from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from btr_ng.ingestion.nocopo import ingest_nocopo_fixture
from btr_ng.ingestion.quality import build_nocopo_quality_report
from btr_ng.publishing.api_builder import build_public_api
from btr_ng.scoring.engine import score_registry_to_directory
from btr_ng.site_builder.builder import build_site

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "nocopo"
SCORING_CONFIG_PATH = PROJECT_ROOT / "spec" / "scoring.toml"
SITE_TEMPLATE_DIR = PROJECT_ROOT / "site" / "templates"
SITE_STATIC_DIR = PROJECT_ROOT / "site" / "static"
STALE_FAILURE_NOTE = (
    "Procurement-linked signals may be stale because the most recent ingestion run failed."
)


def test_ingestion_quality_report_counts_and_mapping_warnings(tmp_path: Path) -> None:
    derived_nocopo_dir = tmp_path / "derived" / "nocopo"
    reports_dir = tmp_path / "derived" / "reports"
    ingest_nocopo_fixture(
        input_path=FIXTURE_DIR / "sample.json",
        registry_dir=REGISTRY_DIR,
        out_dir=derived_nocopo_dir,
    )

    report = build_nocopo_quality_report(
        input_path=FIXTURE_DIR / "sample.json",
        derived_dir=derived_nocopo_dir,
        out_dir=reports_dir,
        ingestion_status="healthy",
        max_age_days=30,
        evaluated_at=datetime(2026, 4, 7, tzinfo=UTC),
    )

    assert report.release_count == 2
    assert report.supplier_count == 2
    assert report.matched_record_count == 2
    assert report.buyer_count == 1
    assert report.contracts_count == 0
    assert report.mapping_warning_count == 0
    assert report.anomaly_count == 1
    assert report.stale is True
    assert report.staleness_reason == "source_snapshot_too_old"


def test_ingestion_quality_report_marks_failed_or_old_inputs_stale(tmp_path: Path) -> None:
    derived_nocopo_dir = tmp_path / "derived" / "nocopo"
    reports_dir = tmp_path / "derived" / "reports"
    ingest_nocopo_fixture(
        input_path=FIXTURE_DIR / "sample.json",
        registry_dir=REGISTRY_DIR,
        out_dir=derived_nocopo_dir,
    )

    failed_report = build_nocopo_quality_report(
        input_path=FIXTURE_DIR / "sample.json",
        derived_dir=derived_nocopo_dir,
        out_dir=reports_dir,
        ingestion_status="failed",
        max_age_days=30,
        evaluated_at=datetime(2026, 4, 7, tzinfo=UTC),
    )
    stale_by_age_report = build_nocopo_quality_report(
        input_path=FIXTURE_DIR / "sample.json",
        derived_dir=derived_nocopo_dir,
        out_dir=reports_dir,
        ingestion_status="healthy",
        max_age_days=2,
        evaluated_at=datetime(2026, 4, 7, tzinfo=UTC),
    )

    assert failed_report.stale is True
    assert failed_report.staleness_reason == "ingestion_failed"
    assert failed_report.anomaly_count == 1
    assert stale_by_age_report.stale is True
    assert stale_by_age_report.staleness_reason == "source_snapshot_too_old"
    assert stale_by_age_report.anomaly_count == 1


def test_stale_procurement_status_is_reflected_in_api_and_site(tmp_path: Path) -> None:
    derived_root = tmp_path / "derived"
    derived_nocopo_dir = derived_root / "nocopo"
    reports_dir = derived_root / "reports"
    score_dir = tmp_path / "scores"
    api_dir = tmp_path / "public" / "api" / "v1"
    site_dir = tmp_path / "site" / "dist"

    ingest_nocopo_fixture(
        input_path=FIXTURE_DIR / "sample.json",
        registry_dir=REGISTRY_DIR,
        out_dir=derived_nocopo_dir,
    )
    build_nocopo_quality_report(
        input_path=FIXTURE_DIR / "sample.json",
        derived_dir=derived_nocopo_dir,
        out_dir=reports_dir,
        ingestion_status="failed",
        max_age_days=30,
        evaluated_at=datetime(2026, 4, 7, tzinfo=UTC),
    )
    score_registry_to_directory(
        registry_dir=REGISTRY_DIR,
        config_path=SCORING_CONFIG_PATH,
        out_dir=score_dir,
    )
    build_public_api(
        registry_dir=REGISTRY_DIR,
        score_dir=score_dir,
        out_dir=api_dir,
        derived_dir=derived_root,
    )
    build_site(
        api_dir=api_dir,
        out_dir=site_dir,
        template_dir=SITE_TEMPLATE_DIR,
        static_dir=SITE_STATIC_DIR,
    )

    index_document = json.loads((api_dir / "index.json").read_text(encoding="utf-8"))
    assert index_document["procurement_data_status"]["stale"] is True
    assert index_document["procurement_data_status"]["ingestion_status"] == "failed"

    acme_document = json.loads(
        (api_dir / "businesses" / "BTR-ACME-001.json").read_text(encoding="utf-8")
    )
    assert acme_document["procurement_data_status"]["public_note"].startswith(
        "Procurement-linked signals may be stale"
    )

    home_html = (site_dir / "index.html").read_text(encoding="utf-8")
    profile_html = (
        site_dir / "businesses" / "BTR-ACME-001" / "index.html"
    ).read_text(encoding="utf-8")
    assert STALE_FAILURE_NOTE in home_html
    assert STALE_FAILURE_NOTE in profile_html
