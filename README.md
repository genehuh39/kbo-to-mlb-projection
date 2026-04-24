# KBO → MLB Projection Tool

Project Major League Baseball performance based on Korean Baseball Organization (KBO) statistics.

## Overview

This tool translates KBO stats into projected MLB equivalents using historical conversion factors derived from players who have made the transition (e.g., Hyun Jin Ryu, Kim Ha-seong, Byung-ho Park, Woo Suk-Young).

KBO production does not directly translate to MLB — park dimensions, ball composition, and league quality differ significantly. This tool accounts for those differences, plus age and role adjustments.

## Quick Start

```bash
# Run the demo (4 example projections)
uv run python kbo_to_mlb.py

# Project a hitter
uv run python kbo_to_mlb.py --type hitter --name "Player Name" --avg 0.300 --ops 0.900 --hr 30 --age 27

# Project a pitcher
uv run python kbo_to_mlb.py --type pitcher --name "Pitcher Name" --era 3.50 --k_per_9 9.0 --whip 1.15 --age 28

# Batch process from JSON
uv run python kbo_to_mlb.py --json kbo_stats.json
```

## Usage

### CLI Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `--type` | `hitter` or `pitcher` | Player type (default: `hitter`) |
| `--name` | string | Player name for display (default: `Player`) |
| `--age` | int | Player age at time of transition (default: `27`) |
| `--role` | `starter` or `reliever` | Pitcher role (default: `starter`) |

**Hitter stats:** `--avg`, `--obp`, `--slg`, `--ops`, `--hr`, `--sb`, `--k_rate`, `--bb_rate`, `--iso`, `--wrc_plus`

**Pitcher stats:** `--era`, `--k_per_9`, `--bb_per_9`, `--whip`, `--hr_per_9`, `--fip`, `--k_bb_ratio`, `--era_plus`

### JSON Input

For batch processing, provide a JSON file:

```json
{
  "avg": 0.310,
  "obp": 0.370,
  "slg": 0.580,
  "ops": 0.950,
  "hr": 35,
  "sb": 5,
  "k_rate": 0.22,
  "bb_rate": 0.07,
  "iso": 0.270,
  "wrc_plus": 145
}
```

```bash
uv run python kbo_to_mlb.py --json kbo_stats.json
```

## Conversion Factors

### Batters

| Stat | KBO → MLB Factor | Rationale |
|------|-------------------|-----------|
| Batting Average | 0.88x | KBO AVG is typically inflated |
| On-Base % | 0.92x | Walks are more valued in MLB |
| Slugging % | 0.82x | KBO parks are smaller, ball flies more |
| OPS | 0.85x | Composite of OBP + SLG |
| Home Runs | 0.72x | KBO parks are smaller, different ball |
| Stolen Bases | 0.90x | Speed translates well |
| Strikeout Rate | 1.20x | MLB pitchers are better |
| Walk Rate | 1.10x | MLB pitchers throw more strikes |
| ISO | 0.75x | KBO ISO is inflated |
| wRC+ | 0.85x | Already league-adjusted |

### Pitchers

| Stat | KBO → MLB Factor | Rationale |
|------|-------------------|-----------|
| ERA | 1.28x | KBO ERA understates MLB struggles |
| K/9 | 1.12x | KBO strikeout rates are lower |
| BB/9 | 0.90x | MLB hitters take fewer bad pitches |
| WHIP | 1.15x | Composite metric |
| HR/9 | 0.80x | KBO home run rate is inflated |
| FIP | 1.20x | Fielding independent metric |
| K/BB Ratio | 0.95x | KBO ratios tend to be lower |
| ERA+ | 0.85x | Already league-adjusted |

### Adjustments

| Factor | Effect |
|--------|--------|
| **Age ≤ 25** | +5% (young stars translate best) |
| **Age 26–28** | Neutral (baseline) |
| **Age 29–31** | −5% penalty |
| **Age 32+** | −10% penalty |
| **KBO Star (OPS > 0.85)** | +5% hitter bonus |
| **Contact Hitter (AVG > 0.300, HR < 15)** | −5% penalty |
| **High-K Pitcher (K/9 > 8.0)** | +5% bonus |
| **Reliever** | −5% penalty |

## Examples

### Power Hitter (KBO Star)
```
KBO: .310 AVG, 35 HR, .950 OPS (age 29)
MLB: .272 AVG, 25 HR, .805 OPS (projected)
```

### Contact/Speed Hitter
```
KBO: .330 AVG, 12 HR, 30 SB (age 26)
MLB: .276 AVG, 8 HR, 26 SB (projected)
```

### Ace Pitcher
```
KBO: 3.20 ERA, 9.5 K/9, 1.10 WHIP (age 28)
MLB: 4.10 ERA, 10.6 K/9, 1.265 WHIP (projected)
```

## Architecture

```
kbo_to_mlb.py
├── factors.json        # Recalibrated conversion factors (loaded at runtime)
├── BATTER_FACTORS      # Conversion multipliers for hitters (from factors.json)
├── PITCHER_FACTORS     # Conversion multipliers for pitchers (from factors.json)
├── age_adjustment_factor()  # Age-based adjustment
├── role_adjustment()        # Role/skill-based adjustment
├── project_batter()         # Main hitter projection
├── project_pitcher()        # Main pitcher projection
├── print_projection()       # Pretty-print output
├── demo()                   # Built-in examples
└── cli()                    # Command-line interface
```

## Requirements

- Python 3.11+
- `uv` (for dependency management)

```bash
uv run python kbo_to_mlb.py
```

## Updating Factors

To update conversion factors without editing the main script, modify `factors.json`:

```bash
cp factors.json factors_backup.json  # backup current factors
# edit factors.json with new values
uv run python kbo_to_mlb.py  # changes take effect immediately
```

To revert to defaults, delete `factors.json` — the script will fall back to built-in values.

## Disclaimer

These are rough translation factors based on aggregate historical data. Individual results vary based on specific skillset, scouting reports, and whether the player was a star in the KBO. Use as a starting point — not a crystal ball.
