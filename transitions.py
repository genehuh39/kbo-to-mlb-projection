#!/usr/bin/env python3
"""Utilities for the KBO-to-MLB transition calibration dataset."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


DATASET_PATH = Path(__file__).parent / "data" / "transitions.csv"


NUMERIC_FIELDS = {
    "transition_age": int,
    "kbo_year": int,
    "kbo_g": int,
    "kbo_pa": int,
    "kbo_ab": int,
    "kbo_ip": float,
    "kbo_avg": float,
    "kbo_obp": float,
    "kbo_slg": float,
    "kbo_ops": float,
    "kbo_hr": int,
    "kbo_sb": int,
    "kbo_bb": int,
    "kbo_so": int,
    "kbo_k_rate": float,
    "kbo_bb_rate": float,
    "kbo_iso": float,
    "kbo_era": float,
    "kbo_whip": float,
    "kbo_hr_per_9": float,
    "kbo_bb_per_9": float,
    "kbo_k_per_9": float,
    "kbo_k_bb_ratio": float,
    "mlb_year": int,
    "mlb_g": int,
    "mlb_pa": int,
    "mlb_ab": int,
    "mlb_ip": float,
    "mlb_avg": float,
    "mlb_obp": float,
    "mlb_slg": float,
    "mlb_ops": float,
    "mlb_hr": int,
    "mlb_sb": int,
    "mlb_bb": int,
    "mlb_so": int,
    "mlb_k_rate": float,
    "mlb_bb_rate": float,
    "mlb_iso": float,
    "mlb_era": float,
    "mlb_whip": float,
    "mlb_hr_per_9": float,
    "mlb_bb_per_9": float,
    "mlb_k_per_9": float,
    "mlb_k_bb_ratio": float,
}


def _coerce_value(key: str, value: str):
    """Convert CSV strings to typed values while preserving blanks as None."""
    if value == "":
        return None

    caster = NUMERIC_FIELDS.get(key)
    if caster is None:
        return value

    return caster(value)


def load_transitions(path: Path = DATASET_PATH) -> list[dict]:
    """Load the transition dataset."""
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return [
            {key: _coerce_value(key, value) for key, value in row.items()}
            for row in reader
        ]


def dataset_summary(rows: list[dict]) -> dict:
    """Return high-level counts for quick auditing."""
    player_types = {}
    paths = {}

    for row in rows:
        player_types[row["player_type"]] = player_types.get(row["player_type"], 0) + 1
        paths[row["transition_path"]] = paths.get(row["transition_path"], 0) + 1

    return {
        "rows": len(rows),
        "player_types": player_types,
        "transition_paths": paths,
        "kbo_year_min": min(row["kbo_year"] for row in rows),
        "kbo_year_max": max(row["kbo_year"] for row in rows),
        "mlb_year_min": min(row["mlb_year"] for row in rows),
        "mlb_year_max": max(row["mlb_year"] for row in rows),
    }


def cli():
    parser = argparse.ArgumentParser(
        description="Inspect the KBO-to-MLB transition calibration dataset.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DATASET_PATH,
        help="Path to transitions.csv.",
    )
    args = parser.parse_args()

    rows = load_transitions(args.path)
    summary = dataset_summary(rows)

    print(f"Rows: {summary['rows']}")
    print(f"Player types: {summary['player_types']}")
    print(f"Transition paths: {summary['transition_paths']}")
    print(f"KBO years: {summary['kbo_year_min']}-{summary['kbo_year_max']}")
    print(f"MLB years: {summary['mlb_year_min']}-{summary['mlb_year_max']}")


if __name__ == "__main__":
    cli()
