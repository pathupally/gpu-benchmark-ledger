from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DIMENSIONS = {
    "gpu_model",
    "memory_gb",
    "form_factor",
    "tier",
    "region",
    "rental_type",
    "observation_window",
    "contributor_coverage",
}


class ProjectValidationError(Exception):
    def __init__(self, issues: list[dict[str, str]]):
        self.issues = issues
        super().__init__(f"project validation failed with {len(issues)} issue(s)")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ProjectValidationError(
                    [{
                        "code": "invalid_jsonl",
                        "location": f"{path}:{line_number}",
                        "message": str(exc),
                    }]
                ) from exc
    return records


def _issue(issues: list[dict[str, str]], code: str, location: str, message: str) -> None:
    issues.append({"code": code, "location": location, "message": message})


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value) is not None
    except ValueError:
        return False


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _validate_schema_node(
    value: Any,
    schema: dict[str, Any],
    location: str,
    issues: list[dict[str, str]],
) -> None:
    expected = schema.get("type")
    if expected is not None:
        candidates = expected if isinstance(expected, list) else [expected]
        if not any(_matches_type(value, candidate) for candidate in candidates):
            _issue(issues, "schema_type", location, f"expected {' or '.join(candidates)}")
            return

    if "enum" in schema and value not in schema["enum"]:
        _issue(issues, "schema_enum", location, f"value must be one of {schema['enum']}")
    if "const" in schema and value != schema["const"]:
        _issue(issues, "schema_const", location, f"value must equal {schema['const']!r}")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            _issue(issues, "schema_min_length", location, "string is too short")
        if schema.get("format") == "date" and not _valid_date(value):
            _issue(issues, "schema_date", location, "expected an ISO 8601 calendar date")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            _issue(issues, "schema_exclusive_minimum", location, f"must be greater than {schema['exclusiveMinimum']}")
        if "minimum" in schema and value < schema["minimum"]:
            _issue(issues, "schema_minimum", location, f"must be at least {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            _issue(issues, "schema_maximum", location, f"must be no more than {schema['maximum']}")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                _issue(issues, "schema_required", f"{location}.{required}", "required property is missing")
        if schema.get("additionalProperties") is False:
            for key in value.keys() - properties.keys():
                _issue(issues, "schema_additional_property", f"{location}.{key}", "property is not allowed")
        for key, child in value.items():
            if key in properties:
                _validate_schema_node(child, properties[key], f"{location}.{key}", issues)


def validate_project(project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    source_dir = root / "data" / "source"
    schema = load_json(root / "schemas" / "benchmark-observation.schema.json")
    registry = load_json(source_dir / "source-registry.json")
    observations = load_jsonl(source_dir / "observations.jsonl")
    pair_book = load_json(source_dir / "benchmark-pairs.json")
    ledger = load_json(source_dir / "methodology-ledger.json")
    issues: list[dict[str, str]] = []

    sources = registry.get("sources", [])
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        location = f"source-registry.sources[{index}]"
        source_id = source.get("source_id")
        if not source_id:
            _issue(issues, "source_id_missing", location, "source_id is required")
        elif source_id in source_ids:
            _issue(issues, "source_id_duplicate", location, f"duplicate source_id {source_id}")
        else:
            source_ids.add(source_id)
        fingerprint = source.get("provenance_fingerprint", "")
        if not SHA256_RE.fullmatch(str(fingerprint)):
            _issue(
                issues,
                "source_fingerprint_invalid",
                f"{location}.provenance_fingerprint",
                "expected 64 lowercase hexadecimal characters",
            )
        if not _valid_date(source.get("retrieved_on")):
            _issue(issues, "source_date_invalid", f"{location}.retrieved_on", "expected an ISO 8601 date")
        if not source.get("upstream_uri"):
            _issue(issues, "source_uri_missing", f"{location}.upstream_uri", "upstream URI is required")
        if not source.get("source_record_locator"):
            _issue(issues, "source_locator_missing", f"{location}.source_record_locator", "source record locator is required")
        if source.get("raw_artifact_redistributed") is not False:
            _issue(
                issues,
                "source_raw_redistribution_invalid",
                f"{location}.raw_artifact_redistributed",
                "public package must not redistribute raw source artifacts",
            )
        if source.get("redistribution_status") != "metadata_and_normalized_derived_records_only":
            _issue(
                issues,
                "source_redistribution_status_invalid",
                f"{location}.redistribution_status",
                "expected normalized-derived-records-only status",
            )
        if "archive_path" in source:
            _issue(
                issues,
                "source_private_path_present",
                f"{location}.archive_path",
                "public source registry cannot reference a private parent archive path",
            )

    methodology_ids: set[str] = set()
    for index, methodology in enumerate(ledger.get("methodologies", [])):
        location = f"methodology-ledger.methodologies[{index}]"
        version = methodology.get("methodology_version")
        if not version:
            _issue(issues, "methodology_id_missing", location, "methodology_version is required")
        elif version in methodology_ids:
            _issue(issues, "methodology_id_duplicate", location, f"duplicate methodology_version {version}")
        else:
            methodology_ids.add(version)
        for source_id in methodology.get("source_ids", []):
            if source_id not in source_ids:
                _issue(issues, "methodology_source_unknown", location, f"unknown source_id {source_id}")

    event_ids: set[str] = set()
    for index, event in enumerate(ledger.get("events", [])):
        location = f"methodology-ledger.events[{index}]"
        event_id = event.get("event_id")
        if not event_id:
            _issue(issues, "event_id_missing", location, "event_id is required")
        elif event_id in event_ids:
            _issue(issues, "event_id_duplicate", location, f"duplicate event_id {event_id}")
        else:
            event_ids.add(event_id)
        if not _valid_date(event.get("effective")):
            _issue(issues, "event_date_invalid", f"{location}.effective", "expected an ISO 8601 date")
        if event.get("source_id") not in source_ids:
            _issue(issues, "event_source_unknown", location, f"unknown source_id {event.get('source_id')}")
        for impact_index, impact in enumerate(event.get("impacts", [])):
            low = impact.get("low_pct")
            high = impact.get("high_pct")
            impact_location = f"{location}.impacts[{impact_index}]"
            if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
                _issue(issues, "impact_not_numeric", impact_location, "low_pct and high_pct must be numeric")
            elif low > high:
                _issue(issues, "impact_range_reversed", impact_location, "low_pct cannot exceed high_pct")
            elif low <= -100:
                _issue(issues, "impact_range_invalid", impact_location, "impact must be greater than -100%")

    observations_by_id: dict[str, dict[str, Any]] = {}
    for index, observation in enumerate(observations):
        location = f"observations[{index}]"
        _validate_schema_node(observation, schema, location, issues)
        observation_id = observation.get("observation_id")
        if observation_id in observations_by_id:
            _issue(issues, "observation_id_duplicate", location, f"duplicate observation_id {observation_id}")
        elif observation_id:
            observations_by_id[observation_id] = observation
        if observation.get("source_id") not in source_ids:
            _issue(issues, "observation_source_unknown", location, f"unknown source_id {observation.get('source_id')}")
        if observation.get("methodology_version") not in methodology_ids:
            _issue(issues, "observation_methodology_unknown", location, f"unknown methodology_version {observation.get('methodology_version')}")

    pair_ids: set[str] = set()
    for index, pair in enumerate(pair_book.get("pairs", [])):
        location = f"benchmark-pairs.pairs[{index}]"
        pair_id = pair.get("pair_id")
        if not pair_id:
            _issue(issues, "pair_id_missing", location, "pair_id is required")
        elif pair_id in pair_ids:
            _issue(issues, "pair_id_duplicate", location, f"duplicate pair_id {pair_id}")
        else:
            pair_ids.add(pair_id)

        ornn = observations_by_id.get(pair.get("ornn_observation_id"))
        sd = observations_by_id.get(pair.get("silicon_data_observation_id"))
        if ornn is None:
            _issue(issues, "pair_ornn_missing", location, "Ornn observation does not exist")
        elif ornn.get("vendor") != "ornn":
            _issue(issues, "pair_ornn_vendor", location, "ornn_observation_id does not point to Ornn")
        if sd is None:
            _issue(issues, "pair_sd_missing", location, "Silicon Data observation does not exist")
        elif sd.get("vendor") != "silicon_data":
            _issue(issues, "pair_sd_vendor", location, "silicon_data_observation_id does not point to Silicon Data")
        if ornn and sd:
            if ornn.get("observation_date") != sd.get("observation_date"):
                _issue(issues, "pair_date_mismatch", location, "observations do not share an observation date")
            if ornn.get("dimensions", {}).get("gpu_model") != sd.get("dimensions", {}).get("gpu_model"):
                _issue(issues, "pair_gpu_mismatch", location, "observations do not share a GPU model")
            if ornn.get("unit") != sd.get("unit"):
                _issue(issues, "pair_unit_mismatch", location, "observations do not share a unit")
        comparison_class = pair.get("comparison_class")
        if comparison_class not in {"exact", "mapped", "approximate"}:
            _issue(issues, "pair_class_invalid", location, "comparison_class must be exact, mapped, or approximate")
        if pair.get("confidence_grade") not in {"A", "B", "C", "D"}:
            _issue(issues, "pair_grade_invalid", location, "confidence_grade must be A, B, C, or D")
        if comparison_class == "approximate" and pair.get("analysis_eligible") is not False:
            _issue(issues, "pair_approximate_eligible", location, "approximate comparisons cannot be analysis eligible")
        assessed = [item.get("dimension") for item in pair.get("dimension_assessments", [])]
        if set(assessed) != DIMENSIONS or len(assessed) != len(DIMENSIONS):
            _issue(issues, "pair_dimensions_incomplete", location, "dimension assessments must cover each schema dimension once")
        for assessment in pair.get("dimension_assessments", []):
            if assessment.get("status") not in {"match", "mismatch", "unknown"}:
                _issue(issues, "pair_dimension_status", location, "assessment status must be match, mismatch, or unknown")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "counts": {
            "sources": len(sources),
            "observations": len(observations),
            "pairs": len(pair_book.get("pairs", [])),
            "methodologies": len(ledger.get("methodologies", [])),
            "events": len(ledger.get("events", [])),
        },
    }


def require_valid_project(project_root: Path) -> dict[str, Any]:
    report = validate_project(project_root)
    if not report["valid"]:
        raise ProjectValidationError(report["issues"])
    return report
