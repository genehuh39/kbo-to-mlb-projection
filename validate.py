#!/usr/bin/env python3
"""Backtest KBO-to-MLB projections against sourced transition data."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from kbo_to_mlb import project_batter, project_pitcher
from transitions import DATASET_PATH, load_transitions


HITTER_STATS = [
    "avg",
    "obp",
    "slg",
    "ops",
    "hr",
    "sb",
    "k_rate",
    "bb_rate",
    "iso",
]

PITCHER_STATS = [
    "era",
    "whip",
    "hr_per_9",
    "bb_per_9",
    "k_per_9",
    "k_bb_ratio",
]


def _stats_from_row(row: dict, prefix: str, stats: list[str]) -> dict:
    """Extract projection stat keys from a transition row prefix."""
    result = {}
    for stat in stats:
        value = row.get(f"{prefix}_{stat}")
        if value is not None:
            result[stat] = value
    return result


def _project_row(row: dict) -> dict:
    """Project a single transition row from KBO stats."""
    player_type = row["player_type"]

    if player_type == "hitter":
        kbo_stats = _stats_from_row(row, "kbo", HITTER_STATS)
        projection = project_batter(kbo_stats, age=row["transition_age"])
        actual = _stats_from_row(row, "mlb", HITTER_STATS)
    elif player_type == "pitcher":
        kbo_stats = _stats_from_row(row, "kbo", PITCHER_STATS)
        projection = project_pitcher(
            kbo_stats,
            age=row["transition_age"],
            role=row.get("role") or "starter",
        )
        actual = _stats_from_row(row, "mlb", PITCHER_STATS)
    else:
        raise ValueError(f"Unsupported player_type: {player_type}")

    errors = {}
    for stat, actual_value in actual.items():
        projected_value = projection.get(stat)
        if projected_value is None:
            continue

        error = projected_value - actual_value
        pct_error = None
        if actual_value != 0:
            pct_error = (error / actual_value) * 100

        errors[stat] = {
            "projected": round(projected_value, 4),
            "actual": round(actual_value, 4),
            "error": round(error, 4),
            "abs_error": round(abs(error), 4),
            "pct_error": round(pct_error, 1) if pct_error is not None else None,
        }

    return {
        "player_id": row["player_id"],
        "player_name": row["player_name"],
        "player_type": player_type,
        "role": row.get("role"),
        "transition_age": row["transition_age"],
        "transition_path": row["transition_path"],
        "kbo_year": row["kbo_year"],
        "mlb_year": row["mlb_year"],
        "kbo_stats": kbo_stats,
        "projected": projection,
        "actual": actual,
        "errors": errors,
        "source_url": row.get("source_url"),
        "source_note": row.get("source_note"),
    }


def run_backtest(rows: list[dict]) -> list[dict]:
    """Run projections for all transition rows."""
    return [_project_row(row) for row in rows]


def aggregate_errors(results: list[dict]) -> dict:
    """Calculate MAE, RMSE, bias, and mean percentage error by stat."""
    buckets = defaultdict(list)

    for result in results:
        for stat, err in result["errors"].items():
            buckets[stat].append(err)

    aggregates = {}
    for stat, values in buckets.items():
        errors = [v["error"] for v in values]
        abs_errors = [v["abs_error"] for v in values]
        pct_errors = [v["pct_error"] for v in values if v["pct_error"] is not None]

        aggregates[stat] = {
            "count": len(values),
            "mae": round(sum(abs_errors) / len(abs_errors), 4),
            "rmse": round(math.sqrt(sum(e * e for e in errors) / len(errors)), 4),
            "bias": round(sum(errors) / len(errors), 4),
            "mean_pct_error": round(sum(pct_errors) / len(pct_errors), 1)
            if pct_errors
            else None,
        }

    return dict(sorted(aggregates.items()))


def compute_optimal_factors(rows: list[dict]) -> dict:
    """Compute least-squares one-stat factors from sourced rows."""
    factors = {"hitter": {}, "pitcher": {}}

    groups = {
        "hitter": HITTER_STATS,
        "pitcher": PITCHER_STATS,
    }

    for player_type, stats in groups.items():
        typed_rows = [row for row in rows if row["player_type"] == player_type]
        for stat in stats:
            pairs = [
                (row.get(f"kbo_{stat}"), row.get(f"mlb_{stat}"))
                for row in typed_rows
            ]
            valid = [(kbo, mlb) for kbo, mlb in pairs if kbo is not None and mlb is not None]
            if len(valid) < 2:
                continue

            denominator = sum(kbo * kbo for kbo, _ in valid)
            if denominator == 0:
                continue

            numerator = sum(kbo * mlb for kbo, mlb in valid)
            factors[player_type][stat] = round(numerator / denominator, 4)

    return factors


def _format_value(stat: str, value) -> str:
    if value is None:
        return "N/A"
    if stat in {"hr", "sb"}:
        return f"{value:.0f}"
    if stat in {"avg", "obp", "slg", "ops", "whip", "iso", "k_rate", "bb_rate"}:
        return f"{value:.3f}"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def print_backtest_report(results: list[dict], aggregates: dict, factors: dict):
    """Print a human-readable backtest report."""
    hitters = [r for r in results if r["player_type"] == "hitter"]
    pitchers = [r for r in results if r["player_type"] == "pitcher"]

    print("\n" + "=" * 84)
    print("  KBO -> MLB BACKTEST REPORT")
    print("=" * 84)
    print(f"  Rows: {len(results)} ({len(hitters)} hitters, {len(pitchers)} pitchers)")
    print("  Dataset: data/transitions.csv")

    for label, rows, stats in (
        ("HITTERS", hitters, HITTER_STATS),
        ("PITCHERS", pitchers, PITCHER_STATS),
    ):
        if not rows:
            continue

        print("\n" + "-" * 84)
        print(f"  {label}")
        print("-" * 84)

        for result in rows:
            print(
                f"\n  {result['player_name']} "
                f"({result['kbo_year']} KBO -> {result['mlb_year']} MLB, "
                f"age {result['transition_age']})"
            )
            print(f"  {'Stat':<12} {'Projected':>12} {'Actual':>12} {'Error':>12} {'% Error':>12}")
            print(f"  {'-' * 64}")

            for stat in stats:
                err = result["errors"].get(stat)
                if not err:
                    continue
                pct = "N/A" if err["pct_error"] is None else f"{err['pct_error']:.1f}%"
                print(
                    f"  {stat:<12} "
                    f"{_format_value(stat, err['projected']):>12} "
                    f"{_format_value(stat, err['actual']):>12} "
                    f"{_format_value(stat, err['error']):>12} "
                    f"{pct:>12}"
                )

    print("\n" + "=" * 84)
    print("  AGGREGATE ERROR METRICS")
    print("=" * 84)
    print(f"  {'Stat':<12} {'N':>4} {'MAE':>10} {'RMSE':>10} {'Bias':>10} {'Mean % Err':>12}")
    print(f"  {'-' * 64}")

    for stat, metrics in aggregates.items():
        pct = "N/A" if metrics["mean_pct_error"] is None else f"{metrics['mean_pct_error']:.1f}%"
        print(
            f"  {stat:<12} {metrics['count']:>4} "
            f"{metrics['mae']:>10.4f} {metrics['rmse']:>10.4f} "
            f"{metrics['bias']:>10.4f} {pct:>12}"
        )

    print("\n" + "=" * 84)
    print("  LEAST-SQUARES FACTORS FROM DATASET")
    print("=" * 84)
    for player_type in ("hitter", "pitcher"):
        print(f"\n  {player_type.upper()}")
        for stat, factor in factors[player_type].items():
            print(f"    {stat:<12} {factor:.4f}")
    print()


def cli():
    parser = argparse.ArgumentParser(
        description="Backtest KBO-to-MLB projections against transition data.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
        help="Path to transitions.csv.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of text.",
    )
    args = parser.parse_args()

    try:
        rows = load_transitions(args.dataset)
    except OSError as exc:
        print(f"Error: could not read dataset {args.dataset}: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Error: malformed dataset {args.dataset}: {exc}", file=sys.stderr)
        sys.exit(1)

    results = run_backtest(rows)
    aggregates = aggregate_errors(results)
    factors = compute_optimal_factors(rows)

    if args.json:
        print(
            json.dumps(
                {
                    "dataset": str(args.dataset),
                    "rows": len(rows),
                    "results": results,
                    "aggregates": aggregates,
                    "least_squares_factors": factors,
                },
                indent=2,
            )
        )
    else:
        print_backtest_report(results, aggregates, factors)


if __name__ == "__main__":
    cli()
