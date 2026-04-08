from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.ingestion.nocopo import IngestionError, ingest_nocopo_fixture
from btr_ng.publishing.api_builder import build_public_api
from btr_ng.scoring.engine import score_registry_to_directory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "nocopo"
SCORING_CONFIG_PATH = PROJECT_ROOT / "spec" / "scoring.toml"
runner = CliRunner()


def test_ingest_nocopo_fixture_writes_deterministic_supplier_summaries(tmp_path: Path) -> None:
    out_dir = tmp_path / "derived" / "nocopo"

    written = ingest_nocopo_fixture(
        input_path=FIXTURE_DIR / "sample.json",
        registry_dir=REGISTRY_DIR,
        out_dir=out_dir,
    )

    assert written == 2
    assert (out_dir / "BTR-ACME-001.json").exists()
    assert (out_dir / "BTR-BLUESKY-001.json").exists()

    acme = json.loads((out_dir / "BTR-ACME-001.json").read_text(encoding="utf-8"))
    assert acme == {
        "awards_count": 3,
        "btr_id": "BTR-ACME-001",
        "buyer_diversity_count": 1,
        "buyers": [
            "FEDERAL CAPITAL TERRITORY ADMINISTRATION",
        ],
        "contracts_count": 0,
        "generated_at": "2026-02-24T09:39:00Z",
        "last_seen": "2026-02-24T09:39:00Z",
        "matched_on": "legal_name",
        "ocids": [
            "ocds-gyl66f-2-005234",
        ],
        "source": "nocopo",
        "source_input": "sample.json",
        "supplier_count": 2,
        "supplier_identifier": "",
        "supplier_name": "Insil Services Ltd",
    }

    blue_sky = json.loads((out_dir / "BTR-BLUESKY-001.json").read_text(encoding="utf-8"))
    assert blue_sky["awards_count"] == 1
    assert blue_sky["contracts_count"] == 0
    assert blue_sky["buyer_diversity_count"] == 1
    assert blue_sky["last_seen"] == "2026-02-19T10:23:00Z"
    assert blue_sky["matched_on"] == "legal_name"
    assert blue_sky["supplier_name"] == "Laurmann & Company Ltd"


def test_ingest_nocopo_fixture_rejects_malformed_input(tmp_path: Path) -> None:
    with pytest.raises(IngestionError) as error:
        ingest_nocopo_fixture(
            input_path=FIXTURE_DIR / "malformed.json",
            registry_dir=REGISTRY_DIR,
            out_dir=tmp_path / "derived" / "nocopo",
        )

    assert "release buyer must be an object" in str(error.value)


def test_ingest_nocopo_cli_and_api_builder_consume_derived_metrics(tmp_path: Path) -> None:
    out_dir = tmp_path / "derived" / "nocopo"
    api_dir = tmp_path / "public" / "api" / "v1"
    score_dir = tmp_path / "scores"

    ingest_result = runner.invoke(
        app,
        [
            "ingest-nocopo",
            "--input",
            str(FIXTURE_DIR / "sample.json"),
            "--registry",
            str(REGISTRY_DIR),
            "--out",
            str(out_dir),
        ],
    )

    assert ingest_result.exit_code == 0
    assert "derived NOCOPO records written" in ingest_result.stdout

    score_registry_to_directory(
        registry_dir=REGISTRY_DIR,
        config_path=SCORING_CONFIG_PATH,
        out_dir=score_dir,
    )

    build_public_api(
        registry_dir=REGISTRY_DIR,
        score_dir=score_dir,
        out_dir=api_dir,
        derived_dir=tmp_path / "derived",
    )

    acme_document = json.loads(
        (api_dir / "businesses" / "BTR-ACME-001.json").read_text(encoding="utf-8")
    )
    assert acme_document["derived_records"][0]["path"] == "nocopo/BTR-ACME-001.json"
    assert acme_document["derived_records"][0]["document"]["awards_count"] == 3
    assert acme_document["derived_records"][0]["document"]["contracts_count"] == 0
