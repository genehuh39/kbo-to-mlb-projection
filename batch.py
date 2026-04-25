#!/usr/bin/env python3
"""Batch processing pipeline for KBO→MLB projections.

Processes multiple players at once, supporting:
- JSON and CSV input formats
- Filtering by stat thresholds
- Multiple output formats (JSON, CSV, text report)

Usage:
    # Process a JSON file of KBO players
    uv run python batch.py --input kbo_players.json

    # Process a CSV file, filter by min HR and OPS
    uv run python batch.py --input kbo_players.csv --filter-hr 15 --filter-ops 0.80

    # Output as CSV
    uv run python batch.py --input kbo_players.json --output csv

    # Show top 10 projected home run hitters
    uv run python batch.py --input kbo_players.json --sort hr --limit 10
"""

import argparse
import csv
import json
import sys
from pathlib import Path

# Import the projection engine
from kbo_to_mlb import (
    project_batter,
    project_pitcher,
    print_projection,
)


def load_json(filepath: str) -> list[dict]:
    """Load player data from a JSON file.

    Expected format:
    [
        {
            "name": "Player Name",
            "age": 27,
            "position": "SS",
            "avg": 0.310,
            "ops": 0.850,
            ...
        },
        ...
    ]

    Or for pitchers:
    [
        {
            "name": "Pitcher Name",
            "age": 30,
            "era": 3.10,
            "k_per_9": 9.8,
            ...
        },
        ...
    ]

    Args:
        filepath: Path to JSON file.

    Returns:
        List of player dictionaries.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Error: JSON file must contain a list of players.", file=sys.stderr)
        sys.exit(1)

    if len(data) == 0:
        print("Error: JSON file is empty.", file=sys.stderr)
        sys.exit(1)

    return data


def load_csv(filepath: str) -> list[dict]:
    """Load player data from a CSV file.

    Expected format: CSV with headers matching stat names (avg, ops, hr, etc.)
    First column should be 'name', second should be 'age'.

    Args:
        filepath: Path to CSV file.

    Returns:
        List of player dictionaries.
    """
    players = []
    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            player = {}

            # Name and age are required
            player["name"] = row.get("name", "Unknown").strip()
            age_str = row.get("age", "").strip()

            if age_str:
                try:
                    player["age"] = int(age_str)
                except ValueError:
                    print(f"Warning: Invalid age '{age_str}' for {player['name']}, using 27", file=sys.stderr)
                    player["age"] = 27
            else:
                player["age"] = 27

            # Position is optional
            position = row.get("position", "").strip()
            if position:
                player["position"] = position

            # Stats (numeric values)
            for key, value in row.items():
                if key in ("name", "age", "position"):
                    continue

                value = value.strip() if isinstance(value, str) else value

                # Try to convert to float
                try:
                    if "." in str(value):
                        player[key] = float(value)
                    else:
                        player[key] = int(float(value))  # Handle "18.0" → 18
                except (ValueError, TypeError):
                    # Skip non-numeric values
                    pass

            players.append(player)

    if len(players) == 0:
        print("Error: CSV file is empty.", file=sys.stderr)
        sys.exit(1)

    return players


def classify_player(player: dict) -> str:
    """Determine if a player is a hitter or pitcher based on available stats.

    Args:
        player: Player dictionary with KBO stats.

    Returns:
        'hitter' or 'pitcher'.
    """
    hitter_stats = {"avg", "obp", "slg", "ops", "hr", "sb", "k_rate", "bb_rate", "iso", "wrc_plus"}
    pitcher_stats = {"era", "k_per_9", "bb_per_9", "whip", "hr_per_9", "fip", "k_bb_ratio", "era_plus"}

    hitter_count = sum(1 for s in hitter_stats if s in player)
    pitcher_count = sum(1 for s in pitcher_stats if s in player)

    # If more hitter stats present, classify as hitter
    if hitter_count >= pitcher_count:
        return "hitter"
    else:
        return "pitcher"


def project_player(player: dict) -> dict:
    """Project a single player's MLB stats from KBO data.

    Args:
        player: Player dictionary with KBO stats.

    Returns:
        Dictionary with name, type, and projected MLB stats.
    """
    player_type = classify_player(player)

    if player_type == "hitter":
        projection = project_batter(
            {k: v for k, v in player.items() if k not in ("name", "age", "position")},
            age=player.get("age", 27),
        )
    else:
        role = player.get("position", "").upper()
        if role in ("RP", "RELIEVER"):
            role = "reliever"
        else:
            role = "starter"

        projection = project_pitcher(
            {k: v for k, v in player.items() if k not in ("name", "age", "position")},
            age=player.get("age", 27),
            role=role,
        )

    return {
        "name": player.get("name", "Unknown"),
        "age": player.get("age", 27),
        "position": player.get("position", ""),
        "type": player_type,
        "projection": projection,
    }


def filter_players(players: list[dict], filters: dict) -> list[dict]:
    """Filter players based on projection thresholds.

    Args:
        players: List of projected player dictionaries.
        filters: Dictionary of filter criteria (e.g., {"min_hr": 15, "max_era": 4.0}).

    Returns:
        Filtered list of players.
    """
    result = []

    for player in players:
        proj = player["projection"]
        include = True

        # Filter by minimum home runs
        if "min_hr" in filters:
            if proj.get("hr", 0) < filters["min_hr"]:
                include = False

        # Filter by minimum OPS (hitters only)
        if "min_ops" in filters:
            if proj.get("ops", 0) < filters["min_ops"]:
                include = False

        # Filter by maximum ERA (pitchers only)
        if "min_era" in filters:  # Note: min_era means ERA must be >= this (good pitchers)
            if proj.get("era", 999) > filters["min_era"]:
                include = False

        # Filter by maximum ERA (pitchers only) - using max_era
        if "max_era" in filters:
            if proj.get("era", 0) > filters["max_era"]:
                include = False

        # Filter by minimum wRC+ (hitters only)
        if "min_wrc_plus" in filters:
            if proj.get("wrc_plus", 0) < filters["min_wrc_plus"]:
                include = False

        # Filter by minimum stolen bases (hitters only)
        if "min_sb" in filters:
            if proj.get("sb", 0) < filters["min_sb"]:
                include = False

        # Filter by minimum K/9 (pitchers only)
        if "min_k_per_9" in filters:
            if proj.get("k_per_9", 0) < filters["min_k_per_9"]:
                include = False

        # Filter by maximum WHIP (pitchers only)
        if "max_whip" in filters:
            if proj.get("whip", 999) > filters["max_whip"]:
                include = False

        # Filter by player type
        if "type" in filters:
            if player["type"] != filters["type"]:
                include = False

        # Filter by position (substring match)
        if "position" in filters:
            pos_filter = filters["position"].upper()
            player_pos = player.get("position", "").upper()
            if pos_filter and pos_filter not in player_pos:
                include = False

        if include:
            result.append(player)

    return result


def sort_players(players: list[dict], sort_by: str, reverse: bool = True) -> list[dict]:
    """Sort players by a projection stat.

    Args:
        players: List of projected player dictionaries.
        sort_by: Stat name to sort by (e.g., 'hr', 'ops', 'era').
        reverse: Sort descending (True) or ascending (False).

    Returns:
        Sorted list of players.
    """
    return sorted(players, key=lambda p: p["projection"].get(sort_by, 0), reverse=reverse)


def limit_players(players: list[dict], limit: int) -> list[dict]:
    """Limit the number of players returned.

    Args:
        players: List of projected player dictionaries.
        limit: Maximum number of players to return.

    Returns:
        Limited list of players.
    """
    return players[:limit]


def output_json(players: list[dict], filepath: str):
    """Output results as JSON.

    Args:
        players: List of projected player dictionaries.
        filepath: Output file path (or '-' for stdout).
    """
    output = {
        "total_players": len(players),
        "players": players,
    }

    if filepath == "-":
        print(json.dumps(output, indent=2))
    else:
        with open(filepath, "w") as f:
            json.dump(output, f, indent=2)


def output_csv(players: list[dict], filepath: str):
    """Output results as CSV.

    Args:
        players: List of projected player dictionaries.
        filepath: Output file path (or '-' for stdout).
    """
    # Collect all stat keys from projections
    all_stats = set()
    for player in players:
        all_stats.update(player["projection"].keys())

    # Define output columns
    columns = ["name", "age", "position", "type"] + sorted(all_stats)

    if filepath == "-":
        writer = csv.DictWriter(sys.stdout, fieldnames=columns)
        writer.writeheader()

        for player in players:
            row = {}
            for col in columns:
                # Try metadata first, then projection
                row[col] = player.get(col, "") or player["projection"].get(col, "")
            writer.writerow(row)
    else:
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for player in players:
                row = {}
                for col in columns:
                    # Try metadata first, then projection
                    row[col] = player.get(col, "") or player["projection"].get(col, "")
                writer.writerow(row)


def output_text(players: list[dict], filepath: str):
    """Output results as formatted text report.

    Args:
        players: List of projected player dictionaries.
        filepath: Output file path (or '-' for stdout).
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append(f"  KBO → MLB PROJECTION REPORT")
    lines.append(f"  Total Players: {len(players)}")
    lines.append("=" * 80)

    # Group by type
    hitters = [p for p in players if p["type"] == "hitter"]
    pitchers = [p for p in players if p["type"] == "pitcher"]

    # Hitters section
    if hitters:
        lines.append("")
        lines.append("  BATTERS")
        lines.append("-" * 80)

        for player in hitters:
            proj = player["projection"]
            lines.append(f"\n  {player['name']} (Age: {player['age']}, Pos: {player.get('position', 'N/A')})")

            if "avg" in proj:
                lines.append(f"    AVG: {proj['avg']:.3f}  |  OBP: {proj.get('obp', 0):.3f}  |  SLG: {proj.get('slg', 0):.3f}")
            if "ops" in proj:
                lines.append(f"    OPS: {proj['ops']:.3f}")

            if "hr" in proj:
                lines.append(f"    Home Runs: {proj['hr']:.0f}")

            if "sb" in proj:
                lines.append(f"    Stolen Bases: {proj['sb']:.0f}")

            if "wrc_plus" in proj:
                lines.append(f"    wRC+: {proj['wrc_plus']:.0f}")

            if "k_rate" in proj:
                lines.append(f"    K%: {proj['k_rate']:.3f}  |  BB%: {proj.get('bb_rate', 0):.3f}")

            if "iso" in proj:
                lines.append(f"    ISO: {proj['iso']:.3f}")

    # Pitchers section
    if pitchers:
        lines.append("")
        lines.append("  PITCHERS")
        lines.append("-" * 80)

        for player in pitchers:
            proj = player["projection"]
            lines.append(f"\n  {player['name']} (Age: {player['age']}, Pos: {player.get('position', 'N/A')})")

            if "era" in proj:
                lines.append(f"    ERA: {proj['era']:.2f}")

            if "k_per_9" in proj:
                lines.append(f"    K/9: {proj['k_per_9']:.2f}")

            if "bb_per_9" in proj:
                lines.append(f"    BB/9: {proj['bb_per_9']:.2f}")

            if "whip" in proj:
                lines.append(f"    WHIP: {proj['whip']:.3f}")

            if "hr_per_9" in proj:
                lines.append(f"    HR/9: {proj['hr_per_9']:.2f}")

            if "fip" in proj:
                lines.append(f"    FIP: {proj['fip']:.2f}")

            if "k_bb_ratio" in proj:
                lines.append(f"    K/BB: {proj['k_bb_ratio']:.2f}")

            if "era_plus" in proj:
                lines.append(f"    ERA+: {proj['era_plus']:.0f}")

    lines.append("")
    lines.append("=" * 80)

    output = "\n".join(lines)

    if filepath == "-":
        print(output)
    else:
        with open(filepath, "w") as f:
            f.write(output)


def cli():
    """Command-line interface for batch processing."""
    parser = argparse.ArgumentParser(
        description="Batch process KBO players to MLB projections.",
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input file (JSON or CSV).",
    )

    parser.add_argument(
        "--output", "-o",
        default="-",
        help="Output file path (default: stdout). Use 'json', 'csv', or 'text' extension to auto-detect format.",
    )

    parser.add_argument(
        "--filter-hr",
        type=int,
        help="Filter: minimum projected home runs.",
    )

    parser.add_argument(
        "--filter-ops",
        type=float,
        help="Filter: minimum projected OPS.",
    )

    parser.add_argument(
        "--filter-era",
        type=float,
        help="Filter: maximum projected ERA (pitchers only).",
    )

    parser.add_argument(
        "--filter-wrc_plus",
        type=int,
        help="Filter: minimum projected wRC+.",
    )

    parser.add_argument(
        "--filter-sb",
        type=int,
        help="Filter: minimum projected stolen bases.",
    )

    parser.add_argument(
        "--filter-k_per_9",
        type=float,
        help="Filter: minimum projected K/9 (pitchers only).",
    )

    parser.add_argument(
        "--filter-whip",
        type=float,
        help="Filter: maximum projected WHIP (pitchers only).",
    )

    parser.add_argument(
        "--filter-type",
        choices=["hitter", "pitcher"],
        help="Filter: only show hitters or pitchers.",
    )

    parser.add_argument(
        "--filter-position",
        help="Filter: position substring (e.g., 'SS', 'SP').",
    )

    parser.add_argument(
        "--sort", "-s",
        choices=["hr", "ops", "era", "k_per_9", "wrc_plus", "sb", "whip"],
        help="Sort results by stat (default: order from input file).",
    )

    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Sort in ascending order (default: descending).",
    )

    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Limit number of results.",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show processing progress.",
    )

    args = parser.parse_args()

    # Determine input format from file extension
    input_path = Path(args.input)
    ext = input_path.suffix.lower()

    if ext == ".json":
        players_raw = load_json(args.input)
    elif ext == ".csv":
        players_raw = load_csv(args.input)
    else:
        print(f"Error: Unsupported file format '{ext}'. Use .json or .csv.", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Loaded {len(players_raw)} players from {args.input}", file=sys.stderr)

    # Project all players
    if args.verbose:
        print("Projecting MLB stats...", file=sys.stderr)

    projected = []
    for player in players_raw:
        try:
            proj = project_player(player)
            projected.append(proj)
        except Exception as e:
            print(f"Warning: Failed to project {player.get('name', 'Unknown')}: {e}", file=sys.stderr)

    if args.verbose:
        print(f"Successfully projected {len(projected)} players.", file=sys.stderr)

    # Apply filters
    filters = {}

    if args.filter_hr is not None:
        filters["min_hr"] = args.filter_hr

    if args.filter_ops is not None:
        filters["min_ops"] = args.filter_ops

    if args.filter_era is not None:
        filters["max_era"] = args.filter_era

    if args.filter_wrc_plus is not None:
        filters["min_wrc_plus"] = args.filter_wrc_plus

    if args.filter_sb is not None:
        filters["min_sb"] = args.filter_sb

    if args.filter_k_per_9 is not None:
        filters["min_k_per_9"] = args.filter_k_per_9

    if args.filter_whip is not None:
        filters["max_whip"] = args.filter_whip

    if args.filter_type is not None:
        filters["type"] = args.filter_type

    if args.filter_position is not None:
        filters["position"] = args.filter_position

    if filters:
        projected = filter_players(projected, filters)
        if args.verbose:
            print(f"After filtering: {len(projected)} players.", file=sys.stderr)

    # Sort results
    if args.sort:
        projected = sort_players(projected, args.sort, reverse=not args.reverse)

    # Limit results
    if args.limit:
        projected = limit_players(projected, args.limit)

    # Determine output format from file extension
    if args.output == "-":
        # Default to text for stdout
        output_text(projected, "-")
    else:
        out_ext = Path(args.output).suffix.lower()

        if out_ext == ".json":
            output_json(projected, args.output)
        elif out_ext == ".csv":
            output_csv(projected, args.output)
        else:
            # Default to text for unknown extensions
            output_text(projected, args.output)

    if args.verbose:
        print(f"Output written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    cli()
