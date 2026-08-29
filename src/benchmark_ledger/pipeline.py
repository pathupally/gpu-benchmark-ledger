from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path
from typing import Any

from .validation import load_json, load_jsonl, require_valid_project


MINIMUM_SHARED_RETURNS = 20


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _rounded(value: float) -> float:
    return round(value, 8)


def _pct_from_log(value: float) -> float:
    return _rounded(math.expm1(value) * 100)


def _series_inception(benchmark_id: str, events: list[dict[str, Any]]) -> str | None:
    candidates = [
        event.get("history_start") or event["effective"]
        for event in events
        if event.get("event_type") == "new_index"
        and benchmark_id in event.get("affected_benchmarks", [])
    ]
    return min(candidates) if candidates else None


def _break_sensitivity(
    raw_log_basis: float,
    sd_observation: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    benchmark_id = sd_observation["benchmark_id"]
    observation_date = sd_observation["observation_date"]
    inception = _series_inception(benchmark_id, events)
    applicable: list[dict[str, Any]] = []
    unquantified: list[str] = []
    restated: list[str] = []

    for event in events:
        if event.get("vendor") != "silicon_data" or event["effective"] > observation_date:
            continue
        if inception and event["effective"] < inception:
            continue
        affected = event.get("affected_benchmarks", [])
        is_global = not affected and event.get("event_type") == "acknowledged_jump"
        if benchmark_id not in affected and not is_global:
            continue
        if event.get("restated") is True:
            restated.append(event["event_id"])
            continue
        matching_impacts = [
            impact for impact in event.get("impacts", [])
            if impact.get("benchmark_id") == benchmark_id
        ]
        if matching_impacts:
            applicable.extend({"event_id": event["event_id"], **impact} for impact in matching_impacts)
        elif event.get("impact_status") == "unquantified":
            unquantified.append(event["event_id"])

    low_log = raw_log_basis
    high_log = raw_log_basis
    for impact in applicable:
        low_log += math.log1p(impact["low_pct"] / 100)
        high_log += math.log1p(impact["high_pct"] / 100)

    if unquantified:
        status = "partial_unbounded" if applicable else "unbounded"
    elif applicable:
        status = "quantified"
    else:
        status = "no_quantified_nonrestated_break"

    return {
        "status": status,
        "is_fully_bounded": not unquantified,
        "series_inception": inception,
        "adjusted_log_low": _rounded(low_log),
        "adjusted_log_high": _rounded(high_log),
        "adjusted_pct_low": _pct_from_log(low_log),
        "adjusted_pct_high": _pct_from_log(high_log),
        "applied_breaks": applicable,
        "unquantified_break_ids": unquantified,
        "restated_break_ids_excluded": restated,
    }


def compute_analysis(project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    require_valid_project(root)
    source_dir = root / "data" / "source"
    observations = load_jsonl(source_dir / "observations.jsonl")
    pair_book = load_json(source_dir / "benchmark-pairs.json")
    ledger = load_json(source_dir / "methodology-ledger.json")
    registry = load_json(source_dir / "source-registry.json")
    by_id = {row["observation_id"]: row for row in observations}

    results: list[dict[str, Any]] = []
    for pair in pair_book["pairs"]:
        ornn = by_id[pair["ornn_observation_id"]]
        sd = by_id[pair["silicon_data_observation_id"]]
        raw_log = math.log(ornn["value"]) - math.log(sd["value"])
        raw_pct = math.expm1(raw_log) * 100
        sensitivity = _break_sensitivity(raw_log, sd, ledger["events"])
        results.append({
            "pair_id": pair["pair_id"],
            "gpu_model": pair["gpu_model"],
            "observation_date": ornn["observation_date"],
            "ornn": {
                "benchmark_id": ornn["benchmark_id"],
                "ticker": ornn["ticker"],
                "value": ornn["value"],
                "source_id": ornn["source_id"],
                "methodology_version": ornn["methodology_version"],
                "dimensions": ornn["dimensions"],
            },
            "silicon_data": {
                "benchmark_id": sd["benchmark_id"],
                "ticker": sd["ticker"],
                "value": sd["value"],
                "source_id": sd["source_id"],
                "methodology_version": sd["methodology_version"],
                "dimensions": sd["dimensions"],
            },
            "basis": {
                "orientation": "Ornn relative to Silicon Data",
                "raw_log": _rounded(raw_log),
                "raw_pct": _rounded(raw_pct),
                "break_sensitivity": sensitivity,
            },
            "comparison_class": pair["comparison_class"],
            "confidence_grade": pair["confidence_grade"],
            "analysis_eligible": pair["analysis_eligible"],
            "rationale": pair["rationale"],
            "dimension_assessments": pair["dimension_assessments"],
        })

    results.sort(key=lambda row: row["gpu_model"])
    eligible = [row for row in results if row["analysis_eligible"]]
    sign_reversal = any(row["basis"]["raw_pct"] < 0 for row in results) and any(
        row["basis"]["raw_pct"] > 0 for row in results
    )
    observed_levels = 1 if results else 0
    observed_returns = max(0, observed_levels - 1)
    analytics_gate = {
        "status": "unavailable",
        "observed_shared_levels": observed_levels,
        "observed_shared_returns": observed_returns,
        "minimum_shared_returns": MINIMUM_SHARED_RETURNS,
        "levels_required": MINIMUM_SHARED_RETURNS + 1,
        "reason": "A rolling estimate requires at least 20 shared daily returns. Only one matched cross-section is archived.",
    }
    retrieved_dates = [source["retrieved_on"] for source in registry["sources"]]

    return {
        "meta": {
            "schema_version": "1.0.0",
            "generated_on": max(retrieved_dates),
            "basis_orientation": pair_book["basis_orientation"],
            "unit": "USD_per_GPU_hour",
            "data_policy": "as-published observations; no inferred history",
        },
        "headline": {
            "matched_cells": len(results),
            "decision_eligible_cells": len(eligible),
            "approximate_cells": len(results) - len(eligible),
            "sign_reversal_present": sign_reversal,
            "largest_absolute_basis": max(results, key=lambda row: abs(row["basis"]["raw_pct"]))["gpu_model"],
        },
        "pairs": results,
        "analytics": {
            "correlation": dict(analytics_gate),
            "rolling_hedge_ratio": dict(analytics_gate),
            "hedge_effectiveness": {
                "status": "unavailable",
                "reason": "No participant-level cash-price panel is present. Benchmark disagreement is not hedge effectiveness.",
            },
        },
        "coverage": [
            {
                "pair_id": row["pair_id"],
                "gpu_model": row["gpu_model"],
                "confidence_grade": row["confidence_grade"],
                "comparison_class": row["comparison_class"],
                "dimensions": row["dimension_assessments"],
            }
            for row in results
        ],
        "methodologies": ledger["methodologies"],
        "events": sorted(ledger["events"], key=lambda event: (event["effective"], event["event_id"]), reverse=True),
        "sources": registry["sources"],
    }


def _json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _csv_text(pairs: list[dict[str, Any]]) -> str:
    fields = [
        "observation_date",
        "gpu_model",
        "ornn_benchmark_id",
        "ornn_value",
        "silicon_data_benchmark_id",
        "silicon_data_value",
        "raw_log_basis",
        "raw_basis_pct",
        "break_adjusted_low_pct",
        "break_adjusted_high_pct",
        "sensitivity_status",
        "comparison_class",
        "confidence_grade",
        "analysis_eligible",
    ]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in pairs:
        sensitivity = row["basis"]["break_sensitivity"]
        writer.writerow({
            "observation_date": row["observation_date"],
            "gpu_model": row["gpu_model"],
            "ornn_benchmark_id": row["ornn"]["benchmark_id"],
            "ornn_value": row["ornn"]["value"],
            "silicon_data_benchmark_id": row["silicon_data"]["benchmark_id"],
            "silicon_data_value": row["silicon_data"]["value"],
            "raw_log_basis": row["basis"]["raw_log"],
            "raw_basis_pct": row["basis"]["raw_pct"],
            "break_adjusted_low_pct": sensitivity["adjusted_pct_low"],
            "break_adjusted_high_pct": sensitivity["adjusted_pct_high"],
            "sensitivity_status": sensitivity["status"],
            "comparison_class": row["comparison_class"],
            "confidence_grade": row["confidence_grade"],
            "analysis_eligible": str(row["analysis_eligible"]).lower(),
        })
    return buffer.getvalue()


def build(project_root: Path | None = None, output_root: Path | None = None) -> dict[str, Any]:
    root = (project_root or default_project_root()).resolve()
    destination = (output_root or root).resolve()
    report = require_valid_project(root)
    analysis = compute_analysis(root)
    generated_dir = destination / "data" / "generated"
    web_dir = destination / "web"
    generated_dir.mkdir(parents=True, exist_ok=True)
    web_dir.mkdir(parents=True, exist_ok=True)

    (generated_dir / "validation-report.json").write_text(_json_text(report), encoding="utf-8")
    (generated_dir / "matched-basis.json").write_text(_json_text({"pairs": analysis["pairs"]}), encoding="utf-8")
    (generated_dir / "matched-basis.csv").write_text(_csv_text(analysis["pairs"]), encoding="utf-8")
    (generated_dir / "dashboard.json").write_text(_json_text(analysis), encoding="utf-8")
    browser_payload = "window.BENCHMARK_LEDGER_DATA = " + json.dumps(
        analysis, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    (web_dir / "data.generated.js").write_text(browser_payload, encoding="utf-8")
    return analysis


def clean(project_root: Path | None = None) -> list[Path]:
    root = (project_root or default_project_root()).resolve()
    targets = [
        root / "data" / "generated" / "validation-report.json",
        root / "data" / "generated" / "matched-basis.json",
        root / "data" / "generated" / "matched-basis.csv",
        root / "data" / "generated" / "dashboard.json",
        root / "web" / "data.generated.js",
    ]
    removed: list[Path] = []
    for target in targets:
        if target.is_file():
            target.unlink()
            removed.append(target)
    return removed

