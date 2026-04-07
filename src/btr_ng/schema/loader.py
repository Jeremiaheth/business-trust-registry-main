"""Load and compile canonical JSON schemas for BTR-NG."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

SCHEMA_FILENAMES = {
    "business-record": "business-record.schema.json",
    "evidence-item": "evidence-item.schema.json",
    "trust-score": "trust-score.schema.json",
    "dispute-record": "dispute-record.schema.json",
    "queue-status": "queue-status.schema.json",
    "privacy-posture": "privacy-posture.schema.json",
}

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "spec" / "schema"


class SchemaLoadError(ValueError):
    """Raised when a schema cannot be found or parsed."""


class SchemaValidationError(ValueError):
    """Raised when a document does not match a schema."""

    def __init__(self, schema_name: str, issues: list[str]) -> None:
        self.schema_name = schema_name
        self.issues = tuple(issues)
        joined = "; ".join(issues)
        super().__init__(f"{schema_name}: {joined}")


def iter_schema_names() -> tuple[str, ...]:
    """Return all known schema names in a deterministic order."""
    return tuple(SCHEMA_FILENAMES)


def get_schema_path(schema_name: str) -> Path:
    """Resolve a canonical schema name to an on-disk path."""
    try:
        filename = SCHEMA_FILENAMES[schema_name]
    except KeyError as error:
        raise SchemaLoadError(f"unknown schema '{schema_name}'") from error

    return SCHEMA_DIR / filename


def load_schema(schema_name: str) -> dict[str, Any]:
    """Read a schema document from disk."""
    path = get_schema_path(schema_name)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SchemaLoadError(f"missing schema file: {path}") from error
    except json.JSONDecodeError as error:
        raise SchemaLoadError(f"failed to parse {path.name}: {error}") from error

    if not isinstance(data, dict):
        raise SchemaLoadError(f"{path.name} must contain a top-level JSON object")
    return cast(dict[str, Any], data)


def load_validator(schema_name: str) -> Draft202012Validator:
    """Compile a Draft 2020-12 validator for the named schema."""
    schema = load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def validate_document(schema_name: str, document: Any) -> None:
    """Validate a document and raise with actionable issues on failure."""
    validator = load_validator(schema_name)
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if errors:
        raise SchemaValidationError(
            schema_name,
            [_format_error(error) for error in errors],
        )


def _format_error(error: ValidationError) -> str:
    path = ".".join(str(item) for item in error.absolute_path)
    display_path = path if path else "$"
    return f"{display_path}: {error.message}"
