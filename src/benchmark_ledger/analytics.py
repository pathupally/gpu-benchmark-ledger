from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Iterable


HEDGE_WINDOW = 20
MINIMUM_HEDGE_LEVELS = 61
MINIMUM_BASIS_OBSERVATIONS = 120
STRICT_DIMENSIONS = ("gpu_model", "tier", "rental_type")


def _rounded(value: float) -> float:
    return round(value, 8)


def _variance(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = statistics.fmean(values)
    return statistics.fmean((value - mean) ** 2 for value in values)


def _covariance(left: list[float], right: list[float]) -> float:
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    return statistics.fmean(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right, strict=True)
    )


def _unavailable(reason: str, observed_count: int, required_count: int) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": reason,
        "observed_count": observed_count,
        "required_count": required_count,
    }


def cross_benchmark_tracking(
    dates: list[str],
    silicon_data_levels: list[float],
    ornn_levels: list[float],
    *,
    window: int = HEDGE_WINDOW,
    minimum_levels: int = MINIMUM_HEDGE_LEVELS,
) -> dict[str, Any]:
    """Estimate a lagged minimum-variance cross-benchmark tracking hedge.

    The coefficient applied on date t is estimated from the preceding ``window``
    returns only. This is benchmark-to-benchmark tracking effectiveness, not a
    futures hedge and not hedge effectiveness for a participant's cash exposure.
    """
    if not (len(dates) == len(silicon_data_levels) == len(ornn_levels)):
        raise ValueError("dates and level series must have equal lengths")
    if any(value <= 0 for value in silicon_data_levels + ornn_levels):
        raise ValueError("benchmark levels must be positive")
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("dates must be unique and ascending")
    if window < 2:
        raise ValueError("window must be at least two returns")

    observed = len(dates)
    if observed < minimum_levels:
        result = _unavailable(
            "Cross-benchmark tracking requires at least 61 matched levels so a "
            "20-return coefficient can be applied to a non-trivial out-of-sample window.",
            observed,
            minimum_levels,
        )
        result.update({
            "estimand": "cross-benchmark tracking effectiveness",
            "window_returns": window,
        })
        return result

    sd_returns = [
        math.log(silicon_data_levels[index] / silicon_data_levels[index - 1])
        for index in range(1, observed)
    ]
    ornn_returns = [
        math.log(ornn_levels[index] / ornn_levels[index - 1])
        for index in range(1, observed)
    ]
    evaluations: list[dict[str, Any]] = []
    for return_index in range(window, len(sd_returns)):
        training_sd = sd_returns[return_index - window:return_index]
        training_ornn = ornn_returns[return_index - window:return_index]
        denominator = _variance(training_ornn)
        if denominator <= 0:
            continue
        beta = _covariance(training_sd, training_ornn) / denominator
        unhedged = sd_returns[return_index]
        tracker = ornn_returns[return_index]
        evaluations.append({
            "date": dates[return_index + 1],
            "training_start": dates[return_index - window],
            "training_end": dates[return_index],
            "beta": _rounded(beta),
            "silicon_data_return": _rounded(unhedged),
            "ornn_return": _rounded(tracker),
            "tracked_residual": _rounded(unhedged - beta * tracker),
        })

    if len(evaluations) < 2:
        result = _unavailable(
            "The matched panel does not contain two valid out-of-sample returns with "
            "non-zero Ornn training variance.",
            len(evaluations),
            2,
        )
        result.update({
            "estimand": "cross-benchmark tracking effectiveness",
            "window_returns": window,
        })
        return result

    unhedged_returns = [row["silicon_data_return"] for row in evaluations]
    residual_returns = [row["tracked_residual"] for row in evaluations]
    unhedged_variance = _variance(unhedged_returns)
    if unhedged_variance <= 0:
        result = _unavailable(
            "Silicon Data returns have zero out-of-sample variance.",
            len(evaluations),
            2,
        )
        result.update({
            "estimand": "cross-benchmark tracking effectiveness",
            "window_returns": window,
        })
        return result

    return {
        "status": "available",
        "estimand": "cross-benchmark tracking effectiveness",
        "interpretation": (
            "Variance reduction when tracking Silicon Data returns with lagged Ornn "
            "returns; not futures or participant cash-exposure hedge effectiveness."
        ),
        "observed_count": observed,
        "required_count": minimum_levels,
        "window_returns": window,
        "out_of_sample_returns": len(evaluations),
        "variance_untracked": _rounded(unhedged_variance),
        "variance_tracked_residual": _rounded(_variance(residual_returns)),
        "variance_reduction": _rounded(1 - _variance(residual_returns) / unhedged_variance),
        "evaluations": evaluations,
    }


def _strict_pair_issues(
    ornn: dict[str, Any], silicon_data: dict[str, Any]
) -> list[str]:
    issues: list[str] = []
    for field in ("observation_date", "unit", "statistic"):
        if ornn.get(field) != silicon_data.get(field):
            issues.append(f"{field}_mismatch")
    for dimension in STRICT_DIMENSIONS:
        ornn_value = ornn["dimensions"].get(dimension)
        sd_value = silicon_data["dimensions"].get(dimension)
        if ornn_value is None or sd_value is None:
            issues.append(f"{dimension}_unknown")
        elif ornn_value != sd_value:
            issues.append(f"{dimension}_mismatch")
    return issues


def matched_basis_monitor(
    observations: Iterable[dict[str, Any]],
    pairs: Iterable[dict[str, Any]],
    *,
    minimum_observations: int = MINIMUM_BASIS_OBSERVATIONS,
) -> dict[str, Any]:
    """Build strict matched-specification basis series and its inference gate."""
    by_id = {row["observation_id"]: row for row in observations}
    series: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exclusions: list[dict[str, Any]] = []
    candidate_count = 0

    for pair in pairs:
        candidate_count += 1
        ornn = by_id[pair["ornn_observation_id"]]
        sd = by_id[pair["silicon_data_observation_id"]]
        issues = _strict_pair_issues(ornn, sd)
        if issues:
            exclusions.append({"pair_id": pair["pair_id"], "reasons": issues})
            continue
        log_basis = math.log(ornn["value"] / sd["value"])
        series[pair["gpu_model"]].append({
            "pair_id": pair["pair_id"],
            "date": ornn["observation_date"],
            "silicon_data": sd["value"],
            "ornn": ornn["value"],
            "log_basis": _rounded(log_basis),
            "pct_basis": _rounded(math.expm1(log_basis) * 100),
        })

    output_series: list[dict[str, Any]] = []
    maximum = 0
    for gpu_model, rows in sorted(series.items()):
        rows.sort(key=lambda row: row["date"])
        maximum = max(maximum, len(rows))
        gate = (
            {"status": "available", "observed_count": len(rows), "required_count": minimum_observations}
            if len(rows) >= minimum_observations
            else _unavailable(
                "Persistence and mean-reversion statistics require 120 strictly matched daily observations.",
                len(rows),
                minimum_observations,
            )
        )
        output_series.append({"gpu_model": gpu_model, "levels": rows, "inference": gate})

    overall = (
        "available"
        if output_series and all(item["inference"]["status"] == "available" for item in output_series)
        else "unavailable"
    )
    return {
        "status": overall,
        "estimand": "strict matched-specification log basis",
        "matching_rule": {
            "root_fields": ["observation_date", "unit", "statistic"],
            "dimensions": list(STRICT_DIMENSIONS),
            "unknown_values_allowed": False,
        },
        "candidate_pairs": candidate_count,
        "admitted_pairs": sum(len(item["levels"]) for item in output_series),
        "observed_count": maximum,
        "required_count": minimum_observations,
        "reason": (
            "No persistence or mean-reversion estimate is reported before one GPU series "
            "contains 120 strictly matched daily observations."
        ),
        "series": output_series,
        "exclusions": exclusions,
    }

