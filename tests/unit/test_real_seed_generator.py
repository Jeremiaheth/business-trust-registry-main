from __future__ import annotations

from pathlib import Path

from btr_ng.registry.validator import validate_registry_dir
from btr_ng.seeding import generate_real_seed, validate_seed_sources

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "data_sources" / "public_seed_sources"


def test_generate_real_seed_is_deterministic_and_schema_valid(tmp_path: Path) -> None:
    registry_a = tmp_path / "registry-a"
    registry_b = tmp_path / "registry-b"
    fixture_a = tmp_path / "sample-a.json"
    fixture_b = tmp_path / "sample-b.json"

    written_a = generate_real_seed(
        source_dir=SOURCE_DIR,
        registry_dir=registry_a,
        nocopo_fixture_out=fixture_a,
    )
    written_b = generate_real_seed(
        source_dir=SOURCE_DIR,
        registry_dir=registry_b,
        nocopo_fixture_out=fixture_b,
    )

    assert written_a == 40
    assert written_b == 40
    assert validate_registry_dir(registry_a) == 40
    assert validate_registry_dir(registry_b) == 40

    files_a = sorted(path.relative_to(tmp_path).as_posix() for path in registry_a.rglob("*.json"))
    files_b = sorted(path.relative_to(tmp_path).as_posix() for path in registry_b.rglob("*.json"))
    assert [path.replace("registry-a", "registry-b") for path in files_a] == files_b

    for relative_path in files_a:
        left = tmp_path / relative_path
        right = tmp_path / relative_path.replace("registry-a", "registry-b")
        assert left.read_text(encoding="utf-8") == right.read_text(encoding="utf-8")

    assert fixture_a.read_text(encoding="utf-8") == fixture_b.read_text(encoding="utf-8")


def test_validate_seed_sources_reports_current_bundle_counts() -> None:
    result = validate_seed_sources(SOURCE_DIR)

    assert result.source_count == 2
    assert result.business_count == 12
    assert result.evidence_reference_count == 26
    assert result.dispute_count == 2
    assert result.fixture_release_count == 11
