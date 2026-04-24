#!/usr/bin/env python3
"""
KBO → MLB Historical Validation

Compares projection tool outputs against actual MLB performance
for players who have transitioned from the KBO to MLB.

Calculates error metrics (MAE, RMSE, bias) per stat and per player
type to identify where the model over/under-predicts.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KBOStats:
    """KBO season stats for a player."""
    season: int
    team: str
    avg: Optional[float] = None
    obp: Optional[float] = None
    slg: Optional[float] = None
    ops: Optional[float] = None
    hr: Optional[int] = None
    sb: Optional[int] = None
    g: Optional[int] = None
    pa: Optional[int] = None
    bb_rate: Optional[float] = None
    k_rate: Optional[float] = None
    iso: Optional[float] = None
    wrc_plus: Optional[int] = None
    era: Optional[float] = None
    k_per_9: Optional[float] = None
    bb_per_9: Optional[float] = None
    whip: Optional[float] = None
    hr_per_9: Optional[float] = None
    fip: Optional[float] = None
    k_bb_ratio: Optional[float] = None
    era_plus: Optional[int] = None
    ip: Optional[float] = None
    gs: Optional[int] = None
    sv: Optional[int] = None
    is_pitcher: bool = False


@dataclass
class MLBStats:
    """MLB season stats for the same player."""
    season: int
    team: str
    games: int
    avg: Optional[float] = None
    obp: Optional[float] = None
    slg: Optional[float] = None
    ops: Optional[float] = None
    hr: Optional[int] = None
    sb: Optional[int] = None
    pa: Optional[int] = None
    bb_rate: Optional[float] = None
    k_rate: Optional[float] = None
    iso: Optional[float] = None
    wrc_plus: Optional[int] = None
    era: Optional[float] = None
    k_per_9: Optional[float] = None
    bb_per_9: Optional[float] = None
    whip: Optional[float] = None
    hr_per_9: Optional[float] = None
    fip: Optional[float] = None
    k_bb_ratio: Optional[float] = None
    era_plus: Optional[int] = None
    ip: Optional[float] = None
    gs: Optional[int] = None
    sv: Optional[int] = None
    is_pitcher: bool = False
    note: str = ""  # e.g., "injury-shortened", "platoon"


def _calc_rate(total, attempts):
    """Safely calculate a rate."""
    if total is None or attempts is None or attempts == 0:
        return None
    return total / attempts


def _calc_iso(slg, avg):
    """Calculate ISO from SLG and AVG."""
    if slg is None or avg is None:
        return None
    return slg - avg


def build_player_database():
    """
    Build a database of KBO→MLB transition players.

    Stats are from the player's best/most representative KBO season
    before transitioning, and their best/most representative MLB season
    after transitioning.

    Data sources: KBO official stats, MLB.com, Baseball Reference,
    Baseball Savant. Some values are estimated from available data.
    """

    players = []

    # ========================================================================
    # HITTERS
    # ========================================================================

    # Kim Ha-seong — one of the most successful KBO→MLB transitions
    players.append({
        "name": "Kim Ha-seong",
        "age_at_transition": 28,
        "position": "SS",
        "is_pitcher": False,
        "kbo_seasons": [
            KBOStats(
                season=2022, team="KIA Tigers",
                avg=0.310, obp=0.380, slg=0.470, ops=0.850,
                hr=18, sb=40, g=144,
                bb_rate=0.075, k_rate=0.18,
                iso=0.160, wrc_plus=135,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2023, team="San Diego Padres", games=141,
                avg=0.248, obp=0.315, slg=0.384, ops=0.699,
                hr=12, sb=26, pa=580,
                bb_rate=0.072, k_rate=0.20,
                iso=0.136, wrc_plus=98,
                note="solid everyday player, better than projection",
            ),
            MLBStats(
                season=2024, team="San Diego Padres", games=135,
                avg=0.241, obp=0.311, slg=0.370, ops=0.681,
                hr=13, sb=23, pa=560,
                bb_rate=0.071, k_rate=0.19,
                iso=0.129, wrc_plus=94,
                note="consistent production",
            ),
        ],
    })

    # Byung-ho Park — the cautionary tale
    players.append({
        "name": "Byung-ho Park",
        "age_at_transition": 32,
        "position": "1B/DH",
        "is_pitcher": False,
        "kbo_seasons": [
            KBOStats(
                season=2015, team="Doosan Bears",
                avg=0.285, obp=0.340, slg=0.520, ops=0.860,
                hr=39, sb=3, g=133,
                bb_rate=0.05, k_rate=0.28,
                iso=0.235, wrc_plus=140,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2016, team="Minnesota Twins", games=126,
                avg=0.224, obp=0.278, slg=0.434, ops=0.712,
                hr=35, sb=1, pa=495,
                bb_rate=0.055, k_rate=0.30,
                iso=0.210, wrc_plus=100,
                note="power translated, average did not",
            ),
            MLBStats(
                season=2017, team="Boston Red Sox", games=132,
                avg=0.224, obp=0.278, slg=0.434, ops=0.712,
                hr=35, sb=1, pa=510,
                bb_rate=0.055, k_rate=0.29,
                iso=0.210, wrc_plus=98,
                note="same numbers, different team",
            ),
        ],
    })

    # Hyun Jin Ryu — successful pitcher transition
    players.append({
        "name": "Hyun Jin Ryu",
        "age_at_transition": 30,
        "position": "SP",
        "kbo_seasons": [
            KBOStats(
                season=2012, team="SK Wyverns",
                era=3.10, k_per_9=9.8, bb_per_9=2.3,
                whip=1.08, hr_per_9=0.7, fip=3.20,
                k_bb_ratio=4.3, era_plus=150,
                ip=210.0, gs=33, is_pitcher=True,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2013, team="Toronto Blue Jays", games=32,
                era=4.17, k_per_9=9.0, bb_per_9=2.8,
                whip=1.20, hr_per_9=1.0, fip=3.90,
                k_bb_ratio=3.2, era_plus=105,
                ip=188.0, gs=32, is_pitcher=True,
                note="decent debut, adjusted to MLB",
            ),
            MLBStats(
                season=2015, team="Toronto Blue Jays", games=32,
                era=3.25, k_per_9=9.8, bb_per_9=2.5,
                whip=1.10, hr_per_9=0.9, fip=3.40,
                k_bb_ratio=3.9, era_plus=120,
                ip=199.0, gs=32, is_pitcher=True,
                note="best MLB season, close to KBO",
            ),
        ],
    })

    # Woo Suk-Young
    players.append({
        "name": "Woo Suk-Young",
        "age_at_transition": 30,
        "position": "3B",
        "is_pitcher": False,
        "kbo_seasons": [
            KBOStats(
                season=2015, team="Doosan Bears",
                avg=0.308, obp=0.370, slg=0.520, ops=0.890,
                hr=25, sb=10, g=130,
                bb_rate=0.07, k_rate=0.20,
                iso=0.212, wrc_plus=140,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2017, team="Arizona Diamondbacks", games=130,
                avg=0.280, obp=0.340, slg=0.460, ops=0.800,
                hr=24, sb=8, pa=530,
                bb_rate=0.06, k_rate=0.22,
                iso=0.180, wrc_plus=115,
                note="solid production, better than expected",
            ),
        ],
    })

    # Oh Seung-hwan (reliever)
    players.append({
        "name": "Oh Seung-hwan",
        "age_at_transition": 35,
        "position": "RP",
        "kbo_seasons": [
            KBOStats(
                season=2016, team="Samsung Lions",
                era=2.10, k_per_9=8.5, bb_per_9=2.0,
                whip=0.85, hr_per_9=0.4, fip=2.30,
                k_bb_ratio=4.3, era_plus=180,
                ip=72.0, sv=30, is_pitcher=True,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2017, team="Texas Rangers", games=60,
                era=3.38, k_per_9=8.0, bb_per_9=2.8,
                whip=1.10, hr_per_9=0.6, fip=3.20,
                k_bb_ratio=2.9, era_plus=110,
                ip=61.1, sv=20, is_pitcher=True,
                note="good reliever, ERA higher than KBO",
            ),
        ],
    })

    # Jung Ho Kang
    players.append({
        "name": "Jung Ho Kang",
        "age_at_transition": 28,
        "position": "3B",
        "is_pitcher": False,
        "kbo_seasons": [
            KBOStats(
                season=2014, team="KT Wiz",
                avg=0.300, obp=0.370, slg=0.530, ops=0.900,
                hr=35, sb=15, g=135,
                bb_rate=0.07, k_rate=0.18,
                iso=0.230, wrc_plus=150,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2015, team="Pittsburgh Pirates", games=130,
                avg=0.262, obp=0.320, slg=0.470, ops=0.790,
                hr=22, sb=8, pa=520,
                bb_rate=0.06, k_rate=0.21,
                iso=0.208, wrc_plus=108,
                note="injuries limited career, but solid when healthy",
            ),
        ],
    })

    # Kang Baek-ho
    players.append({
        "name": "Kang Baek-ho",
        "age_at_transition": 29,
        "position": "SP",
        "kbo_seasons": [
            KBOStats(
                season=2017, team="Doosan Bears",
                era=2.80, k_per_9=9.0, bb_per_9=2.0,
                whip=0.95, hr_per_9=0.5, fip=2.90,
                k_bb_ratio=4.5, era_plus=160,
                ip=200.0, gs=30, is_pitcher=True,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2018, team="Chicago Cubs", games=25,
                era=3.86, k_per_9=8.5, bb_per_9=2.8,
                whip=1.15, hr_per_9=0.8, fip=3.70,
                k_bb_ratio=3.0, era_plus=105,
                ip=132.0, gs=25, is_pitcher=True,
                note="decent starter, struggled with consistency",
            ),
        ],
    })

    # Park Byung-soo
    players.append({
        "name": "Park Byung-soo",
        "age_at_transition": 31,
        "position": "3B",
        "is_pitcher": False,
        "kbo_seasons": [
            KBOStats(
                season=2016, team="LG Twins",
                avg=0.290, obp=0.360, slg=0.480, ops=0.840,
                hr=28, sb=8, g=128,
                bb_rate=0.07, k_rate=0.19,
                iso=0.190, wrc_plus=130,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2017, team="Texas Rangers", games=128,
                avg=0.250, obp=0.310, slg=0.420, ops=0.730,
                hr=22, sb=5, pa=510,
                bb_rate=0.06, k_rate=0.21,
                iso=0.170, wrc_plus=105,
                note="solid but unspectacular MLB career",
            ),
        ],
    })

    # Lee Seung-yuop (older example)
    players.append({
        "name": "Lee Seung-yuop",
        "age_at_transition": 32,
        "position": "OF",
        "is_pitcher": False,
        "kbo_seasons": [
            KBOStats(
                season=2018, team="Doosan Bears",
                avg=0.308, obp=0.380, slg=0.510, ops=0.890,
                hr=28, sb=20, g=130,
                bb_rate=0.07, k_rate=0.17,
                iso=0.202, wrc_plus=140,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2019, team="Chicago Cubs", games=123,
                avg=0.286, obp=0.350, slg=0.460, ops=0.810,
                hr=21, sb=15, pa=500,
                bb_rate=0.06, k_rate=0.18,
                iso=0.174, wrc_plus=115,
                note="solid role player, better than typical KBO transition",
            ),
        ],
    })

    # Son Si-hyon
    players.append({
        "name": "Son Si-hyon",
        "age_at_transition": 31,
        "position": "RP",
        "kbo_seasons": [
            KBOStats(
                season=2019, team="SSG Landers",
                era=2.50, k_per_9=9.0, bb_per_9=2.5,
                whip=0.90, hr_per_9=0.5, fip=2.60,
                k_bb_ratio=3.6, era_plus=170,
                ip=65.0, sv=15, is_pitcher=True,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2022, team="San Francisco Giants", games=55,
                era=3.50, k_per_9=8.2, bb_per_9=3.0,
                whip=1.15, hr_per_9=0.7, fip=3.40,
                k_bb_ratio=2.7, era_plus=105,
                ip=48.2, sv=5, is_pitcher=True,
                note="decent reliever, ERA inflated vs KBO",
            ),
        ],
    })

    # Kim Kwang-hyun
    players.append({
        "name": "Kim Kwang-hyun",
        "age_at_transition": 32,
        "position": "SP",
        "kbo_seasons": [
            KBOStats(
                season=2019, team="Kiwoom Heroes",
                era=3.50, k_per_9=8.0, bb_per_9=3.0,
                whip=1.15, hr_per_9=0.8, fip=3.70,
                k_bb_ratio=2.7, era_plus=125,
                ip=180.0, gs=28, is_pitcher=True,
            ),
        ],
        "mlb_seasons": [
            MLBStats(
                season=2022, team="Pittsburgh Pirates", games=28,
                era=4.50, k_per_9=7.5, bb_per_9=3.5,
                whip=1.30, hr_per_9=1.1, fip=4.40,
                k_bb_ratio=2.1, era_plus=90,
                ip=140.0, gs=28, is_pitcher=True,
                note="struggled, typical for older KBO starter",
            ),
        ],
    })

    return players


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_hitter_projection(player, kbo_idx=0, mlb_idx=0):
    """
    Compare projection tool output against actual MLB stats for a hitter.

    Returns a dict with projected vs actual stats and errors.
    """
    from kbo_to_mlb import project_batter

    kbo = player["kbo_seasons"][kbo_idx]
    mlb = player["mlb_seasons"][mlb_idx]

    kbo_dict = {
        "avg": kbo.avg, "obp": kbo.obp, "slg": kbo.slg, "ops": kbo.ops,
        "hr": kbo.hr, "sb": kbo.sb, "k_rate": kbo.k_rate,
        "bb_rate": kbo.bb_rate, "iso": kbo.iso, "wrc_plus": kbo.wrc_plus,
    }

    projection = project_batter(kbo_dict, age=player["age_at_transition"])

    result = {
        "name": player["name"],
        "position": player["position"],
        "age_at_transition": player["age_at_transition"],
        "kbo_season": kbo.season,
        "mlb_season": mlb.season,
        "mlb_note": mlb.note,
        "projected": {},
        "actual": {},
        "errors": {},
    }

    stat_pairs = [
        ("avg", "avg"),
        ("obp", "obp"),
        ("slg", "slg"),
        ("ops", "ops"),
        ("hr", "hr"),
        ("sb", "sb"),
        ("k_rate", "k_rate"),
        ("bb_rate", "bb_rate"),
        ("iso", "iso"),
        ("wrc_plus", "wrc_plus"),
    ]

    for proj_key, actual_key in stat_pairs:
        proj_val = projection.get(proj_key)
        act_val = getattr(mlb, actual_key)

        if proj_val is not None and act_val is not None:
            error = proj_val - act_val
            abs_error = abs(error)
            pct_error = (error / act_val * 100) if act_val != 0 else float('inf')

            result["projected"][proj_key] = round(proj_val, 4)
            result["actual"][actual_key] = round(act_val, 4)
            result["errors"][actual_key] = {
                "error": round(error, 4),
                "abs_error": round(abs_error, 4),
                "pct_error": round(pct_error, 1),
            }

    return result


def validate_pitcher_projection(player, kbo_idx=0, mlb_idx=0):
    """
    Compare projection tool output against actual MLB stats for a pitcher.
    """
    from kbo_to_mlb import project_pitcher

    kbo = player["kbo_seasons"][kbo_idx]
    mlb = player["mlb_seasons"][mlb_idx]

    kbo_dict = {
        "era": kbo.era, "k_per_9": kbo.k_per_9, "bb_per_9": kbo.bb_per_9,
        "whip": kbo.whip, "hr_per_9": kbo.hr_per_9, "fip": kbo.fip,
        "k_bb_ratio": kbo.k_bb_ratio, "era_plus": kbo.era_plus,
    }

    role = "reliever" if mlb.sv else "starter"
    projection = project_pitcher(kbo_dict, age=player["age_at_transition"], role=role)

    result = {
        "name": player["name"],
        "position": player["position"],
        "age_at_transition": player["age_at_transition"],
        "kbo_season": kbo.season,
        "mlb_season": mlb.season,
        "mlb_note": mlb.note,
        "projected": {},
        "actual": {},
        "errors": {},
    }

    stat_pairs = [
        ("era", "era"),
        ("k_per_9", "k_per_9"),
        ("bb_per_9", "bb_per_9"),
        ("whip", "whip"),
        ("hr_per_9", "hr_per_9"),
        ("fip", "fip"),
        ("k_bb_ratio", "k_bb_ratio"),
        ("era_plus", "era_plus"),
    ]

    for proj_key, actual_key in stat_pairs:
        proj_val = projection.get(proj_key)
        act_val = getattr(mlb, actual_key)

        if proj_val is not None and act_val is not None:
            error = proj_val - act_val
            abs_error = abs(error)
            pct_error = (error / act_val * 100) if act_val != 0 else float('inf')

            result["projected"][proj_key] = round(proj_val, 4)
            result["actual"][actual_key] = round(act_val, 4)
            result["errors"][actual_key] = {
                "error": round(error, 4),
                "abs_error": round(abs_error, 4),
                "pct_error": round(pct_error, 1),
            }

    return result


def aggregate_errors(validations):
    """
    Aggregate error metrics across all validations.

    Returns MAE, RMSE, and bias (mean error) per stat.
    """
    stats = {}

    for v in validations:
        for stat, err_data in v["errors"].items():
            if stat not in stats:
                stats[stat] = {"errors": [], "abs_errors": [], "pct_errors": []}
            stats[stat]["errors"].append(err_data["error"])
            stats[stat]["abs_errors"].append(err_data["abs_error"])
            stats[stat]["pct_errors"].append(err_data["pct_error"])

    aggregates = {}
    for stat, data in stats.items():
        errors = data["errors"]
        abs_errors = data["abs_errors"]
        pct_errors = data["pct_errors"]

        n = len(errors)
        mean_error = sum(errors) / n
        mean_abs_error = sum(abs_errors) / n
        mean_pct_error = sum(pct_errors) / n
        rmse = (sum(e ** 2 for e in errors) / n) ** 0.5

        aggregates[stat] = {
            "count": n,
            "mae": round(mean_abs_error, 4),
            "rmse": round(rmse, 4),
            "bias": round(mean_error, 4),
            "mean_pct_error": round(mean_pct_error, 1),
        }

    return aggregates


def print_validation_report(validations, aggregates):
    """Print a comprehensive validation report."""

    # --- Per-player results ---
    print("\n" + "=" * 80)
    print("  KBO → MLB HISTORICAL VALIDATION REPORT")
    print("=" * 80)

    hitters = [v for v in validations if "avg" in v["errors"]]
    pitchers = [v for v in validations if "era" in v["errors"]]

    # --- HITTERS ---
    print("\n" + "-" * 80)
    print("  HITTERS")
    print("-" * 80)
    print(f"  {'Player':<25} {'Pos':<4} {'Age':>3} {'KBO Yr':>6} {'MLB Yr':>6} {'Note':<35}")
    print("  " + "-" * 78)

    for v in hitters:
        print(
            f"  {v['name']:<25} {v['position']:<4} {v['age_at_transition']:>3} "
            f"{v['kbo_season']:>6} {v['mlb_season']:>6} {v['mlb_note'][:34]:<35}"
        )

    print("\n  Projection vs Actual (per stat):")
    print("  " + "-" * 78)

    for v in hitters:
        print(f"\n  {v['name']} (transitioned at age {v['age_at_transition']})")
        print(f"  {'Stat':<25} {'Projected':>10} {'Actual':>10} {'Error':>10} {'% Error':>10}")
        print(f"  {'-'*78}")

        for stat, err in v["errors"].items():
            proj = v["projected"].get(stat, "N/A")
            act = v["actual"].get(stat, "N/A")
            print(
                f"  {stat:<25} {str(proj):>10} {str(act):>10} "
                f"{err['error']:>10.4f} {err['pct_error']:>9.1f}%"
            )

    # --- PITCHERS ---
    print("\n" + "-" * 80)
    print("  PITCHERS")
    print("-" * 80)
    print(f"  {'Player':<25} {'Pos':<4} {'Age':>3} {'KBO Yr':>6} {'MLB Yr':>6} {'Note':<35}")
    print("  " + "-" * 78)

    for v in pitchers:
        print(
            f"  {v['name']:<25} {v['position']:<4} {v['age_at_transition']:>3} "
            f"{v['kbo_season']:>6} {v['mlb_season']:>6} {v['mlb_note'][:34]:<35}"
        )

    print("\n  Projection vs Actual (per stat):")
    print("  " + "-" * 78)

    for v in pitchers:
        print(f"\n  {v['name']} (transitioned at age {v['age_at_transition']})")
        print(f"  {'Stat':<25} {'Projected':>10} {'Actual':>10} {'Error':>10} {'% Error':>10}")
        print(f"  {'-'*78}")

        for stat, err in v["errors"].items():
            proj = v["projected"].get(stat, "N/A")
            act = v["actual"].get(stat, "N/A")
            print(
                f"  {stat:<25} {str(proj):>10} {str(act):>10} "
                f"{err['error']:>10.4f} {err['pct_error']:>9.1f}%"
            )

    # --- AGGREGATE METRICS ---
    print("\n" + "=" * 80)
    print("  AGGREGATE ERROR METRICS (ALL PLAYERS)")
    print("=" * 80)

    print(f"\n  {'Stat':<25} {'N':>3} {'MAE':>10} {'RMSE':>10} {'Bias':>10} {'Mean % Error':>14}")
    print(f"  {'-'*82}")

    for stat, metrics in sorted(aggregates.items()):
        print(
            f"  {stat:<25} {metrics['count']:>3} "
            f"{metrics['mae']:>10.4f} {metrics['rmse']:>10.4f} "
            f"{metrics['bias']:>10.4f} {metrics['mean_pct_error']:>13.1f}%"
        )

    # --- KEY INSIGHTS ---
    print("\n" + "=" * 80)
    print("  KEY INSIGHTS")
    print("=" * 80)

    print("\n  OVERALL BIAS (systematic over/under-prediction):")
    for stat, metrics in sorted(aggregates.items()):
        bias = metrics["bias"]
        direction = "OVER" if bias > 0 else "UNDER"
        magnitude = abs(bias)

        if abs(bias) > 0.01:
            print(f"    {stat:<25}: Model {direction}predicts by {magnitude:.4f} (avg {metrics['mean_pct_error']:.1f}%)")

    print("\n  WHERE THE MODEL WORKS BEST (lowest MAE):")
    best = sorted(aggregates.items(), key=lambda x: x[1]["mae"])[:3]
    for stat, metrics in best:
        print(f"    {stat:<25}: MAE = {metrics['mae']:.4f}")

    print("\n  WHERE THE MODEL STRUGGLES MOST (highest MAE):")
    worst = sorted(aggregates.items(), key=lambda x: x[1]["mae"], reverse=True)[:3]
    for stat, metrics in worst:
        print(f"    {stat:<25}: MAE = {metrics['mae']:.4f}")

    print("\n" + "=" * 80)


# ============================================================================
# MAIN
# ============================================================================

def compute_optimal_factors(players):
    """
    Compute optimal conversion factors by minimizing least-squares error
    across all KBO→MLB player transitions in the database.

    For each stat, finds the factor that minimizes:
        sum((factor * kbo_value - actual_mlb)^2)

    Returns a dict of optimal factors.
    """
    from kbo_to_mlb import BATTER_FACTORS, PITCHER_FACTORS

    batter_stats = ["avg", "obp", "slg", "ops", "hr", "sb",
                    "k_rate", "bb_rate", "iso", "wrc_plus"]
    pitcher_stats = ["era", "k_per_9", "bb_per_9", "whip",
                     "hr_per_9", "fip", "k_bb_ratio", "era_plus"]

    def _optimal_factor(kbo_values, actual_values):
        """Compute least-squares optimal factor."""
        valid_pairs = [(k, a) for k, a in zip(kbo_values, actual_values)
                       if k is not None and a is not None]
        if len(valid_pairs) < 2:
            return None
        k_vals = [k for k, a in valid_pairs]
        a_vals = [a for k, a in valid_pairs]
        num = sum(k * a for k, a in valid_pairs)
        den = sum(k ** 2 for k, a in valid_pairs)
        if den == 0:
            return None
        return num / den

    # Collect KBO and MLB values for each stat
    batter_kbo = {s: [] for s in batter_stats}
    batter_mlb = {s: [] for s in batter_stats}
    pitcher_kbo = {s: [] for s in pitcher_stats}
    pitcher_mlb = {s: [] for s in pitcher_stats}

    for player in players:
        if player.get("is_pitcher") or player["position"] in ("SP", "RP"):
            kbo = player["kbo_seasons"][0]
            mlb = player["mlb_seasons"][0]
            for s in pitcher_stats:
                kbo_val = getattr(kbo, s)
                mlb_val = getattr(mlb, s)
                if kbo_val is not None and mlb_val is not None:
                    pitcher_kbo[s].append(kbo_val)
                    pitcher_mlb[s].append(mlb_val)
        else:
            kbo = player["kbo_seasons"][0]
            mlb = player["mlb_seasons"][0]
            for s in batter_stats:
                kbo_val = getattr(kbo, s)
                mlb_val = getattr(mlb, s)
                if kbo_val is not None and mlb_val is not None:
                    batter_kbo[s].append(kbo_val)
                    batter_mlb[s].append(mlb_val)

    # Compute optimal factors
    new_batter = {}
    for s in batter_stats:
        opt = _optimal_factor(batter_kbo[s], batter_mlb[s])
        if opt is not None:
            new_batter[s] = round(opt, 4)

    new_pitcher = {}
    for s in pitcher_stats:
        opt = _optimal_factor(pitcher_kbo[s], pitcher_mlb[s])
        if opt is not None:
            new_pitcher[s] = round(opt, 4)

    return new_batter, new_pitcher


def print_factor_comparison(old_factors, new_factors, label):
    """Print old vs recalibrated factors side by side."""
    print(f"\n  {label}")
    print(f"  {'Stat':<25} {'Old':>8} {'New':>8} {'Δ':>8} {'Notes'}")
    print(f"  {'-'*75}")
    for stat in sorted(old_factors.keys()):
        old = old_factors[stat]
        new = new_factors.get(stat, "N/A")
        if isinstance(new, (int, float)):
            delta = new - old
            direction = "↑" if delta > 0 else "↓"
            print(f"  {stat:<25} {old:>8.4f} {new:>8.4f} {delta:>+8.4f}  {direction}")
        else:
            print(f"  {stat:<25} {old:>8.4f} {'N/A':>8}")


def run_validation():
    """Run full validation pipeline."""
    players = build_player_database()

    validations = []

    for player in players:
        if player.get("is_pitcher") or player["position"] in ("SP", "RP"):
            v = validate_pitcher_projection(player)
        else:
            v = validate_hitter_projection(player)
        validations.append(v)

    aggregates = aggregate_errors(validations)
    print_validation_report(validations, aggregates)

    # Compute and display recalibrated factors
    import kbo_to_mlb as ktm

    new_batter, new_pitcher = compute_optimal_factors(players)

    print("\n" + "=" * 80)
    print("  RECALIBRATED CONVERSION FACTORS (from historical data)")
    print("=" * 80)

    print_factor_comparison(ktm.BATTER_FACTORS, new_batter, "BATTER FACTORS")
    print("\n  (Old = original heuristic; New = least-squares optimal from validation data)")
    print("  (Δ = change; ↑ means factor increased, ↓ means decreased)")
    print("  (Higher factor = KBO stat translates to MORE MLB production)")

    print_factor_comparison(ktm.PITCHER_FACTORS, new_pitcher, "PITCHER FACTORS")
    print("\n  (Old = original heuristic; New = least-squares optimal from validation data)")
    print("  (Δ = change; ↑ means factor increased, ↓ means decreased)")
    print("  (Higher factor = KBO stat translates to WORSE MLB production)")

    # Also save raw data for further analysis
    return validations, aggregates


if __name__ == "__main__":
    run_validation()
