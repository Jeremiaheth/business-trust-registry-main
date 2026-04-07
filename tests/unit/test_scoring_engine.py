from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from btr_ng.cli import app
from btr_ng.policy.config import load_ops_config
from btr_ng.safety.controller import build_safety_report
from btr_ng.safety.models import QueueSnapshot, RuntimeSafetyInputs
from btr_ng.scoring.config import load_scoring_config
from btr_ng.scoring.engine import apply_time_decay, score_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "registry"
OPS_DIR = PROJECT_ROOT / "ops"
SCORING_CONFIG_PATH = PROJECT_ROOT / "spec" / "scoring.toml"
GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden" / "scores"
DISPLAY_GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden" / "display"
runner = CliRunner()


def test_time_decay_halves_at_half_life() -> None:
    evaluation_at = datetime(2026, 4, 7, tzinfo=UTC)
    observed_at = datetime(2025, 10, 9, tzinfo=UTC)

    decay = apply_time_decay(
        observed_at=observed_at,
        evaluation_at=evaluation_at,
        half_life_days=180,
        max_age_days=730,
    )

    assert decay == 0.5


def test_score_registry_is_deterministic_across_repeated_runs() -> None:
    first = [snapshot.to_dict() for snapshot in score_registry(REGISTRY_DIR, SCORING_CONFIG_PATH)]
    second = [snapshot.to_dict() for snapshot in score_registry(REGISTRY_DIR, SCORING_CONFIG_PATH)]

    assert first == second


def test_weighted_scores_sum_to_overall_score() -> None:
    config = load_scoring_config(SCORING_CONFIG_PATH)
    snapshots = score_registry(REGISTRY_DIR, SCORING_CONFIG_PATH)
    acme = next(snapshot for snapshot in snapshots if snapshot.btr_id == "BTR-ACME-001")

    weighted_total = round(sum(dimension.weighted_score for dimension in acme.dimensions), 6)

    assert weighted_total == acme.score
    assert len(acme.dimensions) == len(config.dimensions)


def test_seeded_profiles_match_golden_snapshots() -> None:
    snapshots = {
        snapshot.btr_id: snapshot.to_dict()
        for snapshot in score_registry(REGISTRY_DIR, SCORING_CONFIG_PATH)
    }

    for golden_path in sorted(GOLDEN_DIR.glob("*.json")):
        expected = json.loads(golden_path.read_text(encoding="utf-8"))
        assert snapshots[expected["btr_id"]] == expected


def test_display_state_snapshots_cover_strong_low_confidence_disputed_and_maintenance() -> None:
    base_ops = load_ops_config(OPS_DIR)

    normal_snapshots = {
        snapshot.btr_id: snapshot.to_dict()
        for snapshot in score_registry(REGISTRY_DIR, SCORING_CONFIG_PATH)
    }
    disputed_report = build_safety_report(
        RuntimeSafetyInputs(
            ops_config=base_ops,
            queue=QueueSnapshot(claims=0, corrections=0, disputes=1, verifications=0),
            active_disputes=("BTR-BLUESKY-001",),
            ingestion_status="healthy",
        )
    )
    maintenance_report = build_safety_report(
        RuntimeSafetyInputs(
            ops_config=base_ops,
            queue=QueueSnapshot(claims=20, corrections=3, disputes=3, verifications=0),
            active_disputes=(),
            ingestion_status="healthy",
        )
    )
    disputed_snapshots = {
        snapshot.btr_id: snapshot.to_dict()
        for snapshot in score_registry(
            REGISTRY_DIR,
            SCORING_CONFIG_PATH,
            safety_report=disputed_report,
        )
    }
    maintenance_snapshots = {
        snapshot.btr_id: snapshot.to_dict()
        for snapshot in score_registry(
            REGISTRY_DIR,
            SCORING_CONFIG_PATH,
            safety_report=maintenance_report,
        )
    }

    actual_snapshots = {
        "BTR-ACME-001.normal.json": normal_snapshots["BTR-ACME-001"],
        "BTR-BLUESKY-001.low-confidence.json": normal_snapshots["BTR-BLUESKY-001"],
        "BTR-BLUESKY-001.under-review.json": disputed_snapshots["BTR-BLUESKY-001"],
        "BTR-ACME-001.maintenance.json": maintenance_snapshots["BTR-ACME-001"],
    }

    for filename, actual in actual_snapshots.items():
        expected = json.loads((DISPLAY_GOLDEN_DIR / filename).read_text(encoding="utf-8"))
        assert actual == expected


def test_score_cli_writes_snapshot_files(tmp_path: Path) -> None:
    out_dir = tmp_path / "scores"

    result = runner.invoke(
        app,
        [
            "score",
            "--registry",
            str(REGISTRY_DIR),
            "--out",
            str(out_dir),
            "--config",
            str(SCORING_CONFIG_PATH),
        ],
    )

    assert result.exit_code == 0
    assert "3 snapshots" in result.stdout
    assert (out_dir / "BTR-ACME-001.json").exists()
    blue_sky = json.loads((out_dir / "BTR-BLUESKY-001.json").read_text(encoding="utf-8"))
    assert blue_sky["display_state"] == "under_review"
