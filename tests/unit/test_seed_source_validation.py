from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from btr_ng.seeding import RealSeedError, generate_real_seed, validate_seed_sources

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "data_sources" / "public_seed_sources"


def test_validate_seed_sources_rejects_email_like_strings(tmp_path: Path) -> None:
    source_copy = tmp_path / "sources"
    shutil.copytree(SOURCE_DIR, source_copy)
    federal_path = source_copy / "federal_nocopo_2026.source.json"
    federal = json.loads(federal_path.read_text(encoding="utf-8"))
    federal["releases"][0]["awards"][0]["description"] = "contact supplier@example.com for details"
    federal_path.write_text(json.dumps(federal, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(RealSeedError) as error:
        validate_seed_sources(source_copy)

    assert "email-like string" in str(error.value)


def test_validate_seed_sources_rejects_extra_projected_fields(tmp_path: Path) -> None:
    source_copy = tmp_path / "sources"
    shutil.copytree(SOURCE_DIR, source_copy)
    state_path = source_copy / "anambra_state_ocds.source.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["releases"][0]["buyer"]["extra"] = "forbidden"
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(RealSeedError) as error:
        validate_seed_sources(source_copy)

    assert "unsupported fields" in str(error.value)


def test_generate_real_seed_keeps_existing_outputs_when_source_validation_fails(
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "registry"
    fixture_path = tmp_path / "sample.json"
    generate_real_seed(SOURCE_DIR, registry_dir, fixture_path)

    source_copy = tmp_path / "sources"
    shutil.copytree(SOURCE_DIR, source_copy)
    federal_path = source_copy / "federal_nocopo_2026.source.json"
    federal = json.loads(federal_path.read_text(encoding="utf-8"))
    federal["releases"][0]["awards"][0]["description"] = "Call +234 803 381 2808"
    federal_path.write_text(json.dumps(federal, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    before_business = (registry_dir / "businesses" / "btr-acme-insil-services.json").read_text(
        encoding="utf-8"
    )
    before_fixture = fixture_path.read_text(encoding="utf-8")

    with pytest.raises(RealSeedError) as error:
        generate_real_seed(source_copy, registry_dir, fixture_path)

    assert "phone-like string" in str(error.value)
    assert (
        registry_dir / "businesses" / "btr-acme-insil-services.json"
    ).read_text(encoding="utf-8") == before_business
    assert fixture_path.read_text(encoding="utf-8") == before_fixture
