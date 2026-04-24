#!/usr/bin/env python3
"""
KBO to MLB Projection Tool
Projects Major League Baseball performance based on KBO statistics.

Uses historical conversion factors derived from players who transitioned
from the KBO to MLB (e.g., Hyun Jin Ryu, Kim Ha-seong, Byung-ho Park,
Woo Suk-Young, etc.).
"""

import argparse
import json
import sys


# ============================================================================
# CONVERSION FACTORS (KBO → MLB)
#
# These are approximate multipliers based on aggregate historical data
# from players who made the KBO→MLB transition. They represent the
# typical "translation" needed because:
#   - KBO batting average tends to be higher than MLB (easier hitting environment)
#   - KBO home-run rates tend to be inflated (smaller parks, different ball)
#   - KBO strikeout rates are lower (different pitching quality)
#   - Pitchers generally see their ERA increase in MLB
#
# These are rough averages — individual results vary based on age, role,
# specific skillset, and whether the player was a star in the KBO.
# ============================================================================

# ============================================================================
# FACTOR LOADING
#
# Factors are loaded from factors.json (recalibrated from validation data).
# Falls back to built-in defaults if the file is missing or invalid.
# ============================================================================

_DEFAULT_BATTER_FACTORS = {
    "avg": 0.86,
    "obp": 0.87,
    "slg": 0.87,
    "ops": 0.87,
    "hr": 0.79,
    "sb": 0.66,
    "k_rate": 1.10,
    "bb_rate": 0.90,
    "iso": 0.88,
    "wrc_plus": 0.77,
}

_DEFAULT_PITCHER_FACTORS = {
    "era": 1.37,
    "k_per_9": 0.93,
    "bb_per_9": 1.25,
    "whip": 1.19,
    "hr_per_9": 1.44,
    "fip": 1.25,
    "k_bb_ratio": 0.71,
    "era_plus": 0.65,
}


def _load_factors_from_file():
    """Load recalibrated factors from factors.json if available."""
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "factors.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return {
            "batter": data.get("batter_factors", _DEFAULT_BATTER_FACTORS),
            "pitcher": data.get("pitcher_factors", _DEFAULT_PITCHER_FACTORS),
        }
    except (json.JSONDecodeError, KeyError):
        return None

_loaded = _load_factors_from_file()
BATTER_FACTORS = _loaded["batter"] if _loaded else dict(_DEFAULT_BATTER_FACTORS)
PITCHER_FACTORS = _loaded["pitcher"] if _loaded else dict(_DEFAULT_PITCHER_FACTORS)


# ============================================================================
# AGE ADJUSTMENT
#
# Players age 24 and under tend to translate better (more upside).
# Players 30+ tend to struggle more with the jump.
# ============================================================================

def age_adjustment_factor(age):
    """
    Adjust projection based on player age at time of transition.

    - Ages 22-25: +5% boost (young stars translate best)
    - Ages 26-28: neutral (baseline)
    - Ages 29-31: -5% penalty
    - Ages 32+: -10% penalty (older players struggle more)
    """
    if age <= 25:
        return 1.05
    elif age <= 28:
        return 1.00
    elif age <= 31:
        return 0.95
    else:
        return 0.90


# ============================================================================
# POSITION / ROLE ADJUSTMENTS
#
# Some positions/roles translate differently:
# - Power hitters who are stars in KBO tend to translate better
# - Contact hitters tend to struggle more (KBO AVG is inflated)
# - Pitchers with high K/9 rates translate better
# - Relievers vs. starters have different translation curves
# ============================================================================

def role_adjustment(player_type, kbo_stats):
    """
    Apply role-specific adjustments.

    player_type: "hitter", "pitcher", "reliever"
    kbo_stats: dict of KBO stats
    """
    adjustment = 1.0

    if player_type == "hitter":
        # Star hitters (high OPS) translate better than average
        kbo_ops = kbo_stats.get("ops", 0)
        if kbo_ops > 0.85:
            adjustment = 1.05  # star bonus
        elif kbo_ops < 0.70:
            adjustment = 0.95  # average/below-average penalty

        # Pure contact hitters get hit harder in MLB
        kbo_avg = kbo_stats.get("avg", 0)
        kbo_hr = kbo_stats.get("hr", 0)
        if kbo_avg > 0.300 and kbo_hr < 15:
            adjustment *= 0.95  # contact hitters struggle more

    elif player_type == "pitcher":
        # High-K pitchers translate better
        kbo_k9 = kbo_stats.get("k_per_9", 0)
        if kbo_k9 > 8.0:
            adjustment = 1.05  # strikeout pitcher bonus

        # Ground-ball pitchers may struggle more in MLB (smaller parks)
        # (would need GB% data for this — omitted for now)

    elif player_type == "reliever":
        # Relievers often see bigger ERAs in MLB due to lack of
        # "pitch-to-contact" game development
        adjustment = 0.95

    return adjustment


# ============================================================================
# MAIN PROJECTION FUNCTIONS
# ============================================================================

def project_batter(kbo_stats, age=27):
    """
    Project MLB batting stats from KBO stats.

    Args:
        kbo_stats (dict): KBO statistics including:
            - avg: batting average
            - obp: on-base percentage
            - slg: slugging percentage
            - ops: on-base plus slugging
            - hr: home runs (total or per 162 games)
            - sb: stolen bases (total or per 162 games)
            - k_rate: strikeout rate (K/PA or K%)
            - bb_rate: walk rate (BB/PA or BB%)
            - iso: isolated power
            - wrc_plus: weighted runs created plus
        age (int): player's age at time of transition

    Returns:
        dict: projected MLB batting stats
    """
    projected = {}

    for stat, factor in BATTER_FACTORS.items():
        kbo_value = kbo_stats.get(stat)
        if kbo_value is None:
            continue

        # Apply conversion factor
        mlb_value = kbo_value * factor

        # Apply age adjustment
        mlb_value *= age_adjustment_factor(age)

        # Apply role adjustment
        mlb_value *= role_adjustment("hitter", kbo_stats)

        projected[stat] = round(mlb_value, 4) if isinstance(mlb_value, float) else mlb_value

    return projected


def project_pitcher(kbo_stats, age=27, role="starter"):
    """
    Project MLB pitching stats from KBO stats.

    Args:
        kbo_stats (dict): KBO statistics including:
            - era: earned run average
            - k_per_9: strikeouts per 9 innings
            - bb_per_9: walks per 9 innings
            - whip: walks + hits per inning
            - hr_per_9: home runs per 9 innings
            - fip: fielding independent pitching
            - k_bb_ratio: strikeout-to-walk ratio
            - era_plus: ERA+
        age (int): player's age at time of transition
        role (str): "starter" or "reliever"

    Returns:
        dict: projected MLB pitching stats
    """
    projected = {}

    for stat, factor in PITCHER_FACTORS.items():
        kbo_value = kbo_stats.get(stat)
        if kbo_value is None:
            continue

        # Apply conversion factor
        mlb_value = kbo_value * factor

        # Apply age adjustment
        mlb_value *= age_adjustment_factor(age)

        # Apply role adjustment
        mlb_value *= role_adjustment(role, kbo_stats)

        projected[stat] = round(mlb_value, 4) if isinstance(mlb_value, float) else mlb_value

    return projected


def print_projection(projection, player_name="Player", stat_type="hitter"):
    """Pretty-print projection results."""
    print(f"\n{'='*60}")
    print(f"  KBO → MLB Projection: {player_name}")
    print(f"  {'BATTING' if stat_type == 'hitter' else 'PITCHING'}")
    print(f"{'='*60}")

    stat_labels = {
        "avg": "Batting Average",
        "obp": "On-Base Pct",
        "slg": "Slugging Pct",
        "ops": "OPS",
        "hr": "Home Runs",
        "sb": "Stolen Bases",
        "k_rate": "Strikeout Rate",
        "bb_rate": "Walk Rate",
        "iso": "ISO",
        "wrc_plus": "wRC+",
        "era": "ERA",
        "k_per_9": "K/9",
        "bb_per_9": "BB/9",
        "whip": "WHIP",
        "hr_per_9": "HR/9",
        "fip": "FIP",
        "k_bb_ratio": "K/BB Ratio",
        "era_plus": "ERA+",
    }

    for stat, value in projection.items():
        label = stat_labels.get(stat, stat.upper())

        # Format values
        if stat in ["era", "fip"]:
            formatted = f"{value:.2f}"
        elif stat in ["avg", "obp", "slg", "ops", "whip"]:
            formatted = f"{value:.3f}"
        elif stat in ["k_rate", "bb_rate", "k_per_9", "bb_per_9", "hr_per_9"]:
            formatted = f"{value:.2f}"
        else:
            formatted = f"{value:.0f}" if isinstance(value, (int, float)) else str(value)

        print(f"  {label:.<30} {formatted}")

    print(f"{'='*60}\n")


# ============================================================================
# DEMO / EXAMPLES
# ============================================================================

def demo():
    """Run example projections."""
    print("KBO → MLB Projection Tool")
    print("=========================\n")

    # Example 1: A power hitter (like Byung-ho Park)
    power_hitter = {
        "avg": 0.310,
        "obp": 0.370,
        "slg": 0.580,
        "ops": 0.950,
        "hr": 35,
        "sb": 5,
        "k_rate": 0.22,
        "bb_rate": 0.07,
        "iso": 0.270,
        "wrc_plus": 145,
    }

    print("Example 1: Power Hitter (KBO Star)")
    print("-" * 40)
    proj = project_batter(power_hitter, age=29)
    print_projection(proj, "Power Hitter", "hitter")

    # Example 2: A contact hitter (like a typical KBO leadoff)
    contact_hitter = {
        "avg": 0.330,
        "obp": 0.380,
        "slg": 0.420,
        "ops": 0.800,
        "hr": 12,
        "sb": 30,
        "k_rate": 0.12,
        "bb_rate": 0.06,
        "iso": 0.090,
        "wrc_plus": 115,
    }

    print("Example 2: Contact/Speed Hitter")
    print("-" * 40)
    proj = project_batter(contact_hitter, age=26)
    print_projection(proj, "Contact Hitter", "hitter")

    # Example 3: A high-K pitcher (like Hyun Jin Ryu)
    ace_pitcher = {
        "era": 3.20,
        "k_per_9": 9.5,
        "bb_per_9": 2.5,
        "whip": 1.10,
        "hr_per_9": 0.8,
        "fip": 3.40,
        "k_bb_ratio": 3.8,
        "era_plus": 135,
    }

    print("Example 3: Ace Pitcher (High K/9)")
    print("-" * 40)
    proj = project_pitcher(ace_pitcher, age=28, role="starter")
    print_projection(proj, "Ace Pitcher", "pitcher")

    # Example 4: A ground-ball reliever
    reliever = {
        "era": 2.80,
        "k_per_9": 7.5,
        "bb_per_9": 3.0,
        "whip": 1.05,
        "hr_per_9": 0.5,
        "fip": 3.10,
        "k_bb_ratio": 2.5,
        "era_plus": 150,
    }

    print("Example 4: Relief Pitcher")
    print("-" * 40)
    proj = project_pitcher(reliever, age=31, role="reliever")
    print_projection(proj, "Reliever", "pitcher")


# ============================================================================
# CLI INTERFACE
# ============================================================================

def cli():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Project MLB performance from KBO statistics.",
    )

    parser.add_argument(
        "--type",
        choices=["hitter", "pitcher"],
        default="hitter",
        help="Player type (default: hitter)",
    )
    parser.add_argument(
        "--name",
        default="Player",
        help="Player name for display (default: Player)",
    )
    parser.add_argument(
        "--age",
        type=int,
        default=27,
        help="Player age at transition (default: 27)",
    )
    parser.add_argument(
        "--role",
        choices=["starter", "reliever"],
        default="starter",
        help="Pitcher role (default: starter)",
    )

    # Hitter stats
    parser.add_argument("--avg", type=float, help="KBO batting average")
    parser.add_argument("--obp", type=float, help="KBO on-base percentage")
    parser.add_argument("--slg", type=float, help="KBO slugging percentage")
    parser.add_argument("--ops", type=float, help="KBO OPS")
    parser.add_argument("--hr", type=int, help="KBO home runs")
    parser.add_argument("--sb", type=int, help="KBO stolen bases")
    parser.add_argument("--k_rate", type=float, help="KBO strikeout rate (K/PA)")
    parser.add_argument("--bb_rate", type=float, help="KBO walk rate (BB/PA)")
    parser.add_argument("--iso", type=float, help="KBO ISO")
    parser.add_argument("--wrc_plus", type=int, help="KBO wRC+")

    # Pitcher stats
    parser.add_argument("--era", type=float, help="KBO ERA")
    parser.add_argument("--k_per_9", type=float, help="KBO K/9")
    parser.add_argument("--bb_per_9", type=float, help="KBO BB/9")
    parser.add_argument("--whip", type=float, help="KBO WHIP")
    parser.add_argument("--hr_per_9", type=float, help="KBO HR/9")
    parser.add_argument("--fip", type=float, help="KBO FIP")
    parser.add_argument("--k_bb_ratio", type=float, help="KBO K/BB Ratio")
    parser.add_argument("--era_plus", type=int, help="KBO ERA+")

    # JSON file input
    parser.add_argument("--json", help="Path to JSON file with KBO stats")

    args = parser.parse_args()

    # Load from JSON file if provided
    if args.json:
        with open(args.json, "r") as f:
            kbo_stats = json.load(f)
    else:
        # Build stats dict from CLI args
        kbo_stats = {}
        if args.type == "hitter":
            for stat in [
                "avg", "obp", "slg", "ops", "hr", "sb",
                "k_rate", "bb_rate", "iso", "wrc_plus",
            ]:
                val = getattr(args, stat)
                if val is not None:
                    kbo_stats[stat] = val
        else:
            for stat in [
                "era", "k_per_9", "bb_per_9", "whip", "hr_per_9",
                "fip", "k_bb_ratio", "era_plus",
            ]:
                val = getattr(args, stat)
                if val is not None:
                    kbo_stats[stat] = val

    if not kbo_stats:
        print("No stats provided. Run with --help for usage.")
        sys.exit(1)

    # Run projection
    if args.type == "hitter":
        projection = project_batter(kbo_stats, age=args.age)
        print_projection(projection, args.name, "hitter")
    else:
        projection = project_pitcher(
            kbo_stats, age=args.age, role=args.role
        )
        print_projection(projection, args.name, "pitcher")


if __name__ == "__main__":
    # Run demo if no CLI args
    import sys
    if len(sys.argv) == 1:
        demo()
    else:
        cli()
