"""Validate registry JSON files against canonical schemas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from btr_ng.schema import SchemaLoadError, SchemaValidationError, validate_document

REGISTRY_SCHEMA_BY_LANE = {
    "businesses": "business-record",
    "evidence": "evidence-item",
    "disputes": "dispute-record",
}


@dataclass(frozen=True, slots=True)
class RegistryValidationIssue:
    """A single registry validation problem."""

    file_path: Path
    message: str

    def render(self) -> str:
        """Return a user-facing validation message."""
        return f"{self.file_path}: {self.message}"


class RegistryValidationError(ValueError):
    """Raised when registry validation fails."""

    def __init__(self, issues: list[RegistryValidationIssue]) -> None:
        self.issues = tuple(issues)
        joined = "; ".join(issue.render() for issue in issues)
        super().__init__(joined)


def validate_registry_dir(registry_dir: Path) -> int:
    """Validate every JSON file beneath the registry root."""
    if not registry_dir.exists():
        raise RegistryValidationError(
            [RegistryValidationIssue(registry_dir, "registry directory does not exist.")]
        )
    if not registry_dir.is_dir():
        raise RegistryValidationError(
            [RegistryValidationIssue(registry_dir, "registry path must be a directory.")]
        )

    issues: list[RegistryValidationIssue] = []
    json_files = sorted(registry_dir.rglob("*.json"))
    for file_path in json_files:
        issues.extend(_validate_registry_file(registry_dir, file_path))

    if issues:
        raise RegistryValidationError(issues)
    return len(json_files)


def _validate_registry_file(registry_dir: Path, file_path: Path) -> list[RegistryValidationIssue]:
    relative_path = file_path.relative_to(registry_dir)
    lane = relative_path.parts[0] if relative_path.parts else ""
    schema_name = REGISTRY_SCHEMA_BY_LANE.get(lane)
    if schema_name is None:
        supported = ", ".join(sorted(REGISTRY_SCHEMA_BY_LANE))
        return [
            RegistryValidationIssue(
                file_path,
                (
                    f"no schema is configured for registry lane '{lane}'. "
                    f"Supported lanes: {supported}."
                ),
            )
        ]

    try:
        document = _load_json_object(file_path)
        validate_document(schema_name, document)
    except SchemaLoadError as error:
        return [RegistryValidationIssue(file_path, str(error))]
    except SchemaValidationError as error:
        return [
            RegistryValidationIssue(
                file_path,
                f"failed {schema_name} validation: {issue}",
            )
            for issue in error.issues
        ]
    except ValueError as error:
        return [RegistryValidationIssue(file_path, str(error))]

    return []


def _load_json_object(file_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON: {error.msg}") from error

    if not isinstance(data, dict):
        raise ValueError("registry documents must contain a top-level JSON object.")
    return cast(dict[str, Any], data)
