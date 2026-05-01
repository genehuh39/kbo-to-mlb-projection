# KBO → MLB Projection Tool

[![version](https://img.shields.io/badge/version-0.2.0-blue)](https://github.com/genehuh39/kbo-to-mlb-projection/releases)

Project Major League Baseball performance based on Korean Baseball Organization (KBO) statistics.

## Overview

This tool translates KBO stats into projected MLB equivalents using historical conversion factors derived from players who have made the transition (e.g., Hyun Jin Ryu, Kim Ha-seong, Byung-ho Park, Woo Suk-Young).

KBO production does not directly translate to MLB — park dimensions, ball composition, and league quality differ significantly. This tool accounts for those differences, plus age and role adjustments.

## Quick Start

### Live KBO Stats Lookup

```bash
# Search MyKBOStats.com and project directly — no manual stat entry needed!
uv run python kbo_to_mlb.py --lookup "Kang Baekho"

# With multi-year projection and MLB comps
uv run python kbo_to_mlb.py --lookup "Kang Baekho" --multi --comps

# With MLB player comps
uv run python kbo_to_mlb.py --avg 0.310 --ops 0.950 --hr 35 --comps

# Fetch by URL or player ID
uv run python kbo_to_mlb.py --lookup-url "https://mykbostats.com/players/1694"
uv run python kbo_to_mlb.py --lookup-id 1694

# Specify age override
uv run python kbo_to_mlb.py --lookup "Na Gyun-an" --age 26
```

### Single Player Projection (Manual Stats)

```bash
# Run the demo (6 example projections)
uv run python kbo_to_mlb.py

# Project a hitter (single year)
uv run python kbo_to_mlb.py --type hitter --name "Player Name" --avg 0.300 --ops 0.900 --hr 30 --age 27

# Project a pitcher (single year)
uv run python kbo_to_mlb.py --type pitcher --name "Pitcher Name" --era 3.50 --k_per_9 9.0 --whip 1.15 --age 28
```

### Multi-Year Projection (with Confidence Intervals)

```bash
# 3-year projection with 80% and 95% confidence intervals
uv run python kbo_to_mlb.py --type hitter --name "Kim Ha-seong" \
  --avg 0.310 --ops 0.850 --hr 18 --sb 40 --age 28 --multi
```

### Batch Processing (Multiple Players)

```bash
# Process all players from sample data
uv run python batch.py --input sample_kbo_players.json

# Find top 5 projected home run hitters
uv run python batch.py --input sample_kbo_players.json \
  --filter-type hitter --sort hr --limit 5

# Find pitchers who project to <4.00 ERA
uv run python batch.py --input sample_kbo_players.json \
  --filter-type pitcher --filter-era 4.0

# Output as CSV for spreadsheet analysis
uv run python batch.py --input sample_kbo_players.json -o mlb_projections.csv
```

## Batch Processing (`batch.py`)

Process entire KBO rosters at once. Automatically classifies players as hitters or pitchers based on available stats.

### Input Formats

**JSON:**
```json
[
  {
    "name": "Kim Ha-seong",
    "age": 28,
    "position": "SS",
    "avg": 0.310,
    "ops": 0.850,
    "hr": 18,
    "sb": 40,
    "k_rate": 0.18,
    "bb_rate": 0.075
  }
]
```

**CSV:**
```csv
name,age,position,avg,ops,hr,sb,k_rate,bb_rate
Kim Ha-seong,28,SS,0.310,0.850,18,40,0.18,0.075
```

### Filtering (combine as needed)

| Filter | Description | Example |
|--------|-------------|---------|
| `--filter-hr` | Minimum projected home runs | `--filter-hr 25` |
| `--filter-ops` | Minimum projected OPS | `--filter-ops 0.85` |
| `--filter-era` | Maximum projected ERA (pitchers) | `--filter-era 4.0` |
| `--filter-wrc_plus` | Minimum projected wRC+ | `--filter-wrc_plus 120` |
| `--filter-sb` | Minimum projected stolen bases | `--filter-sb 30` |
| `--filter-k_per_9` | Minimum projected K/9 (pitchers) | `--filter-k_per_9 8.0` |
| `--filter-whip` | Maximum projected WHIP (pitchers) | `--filter-whip 1.20` |
| `--filter-type` | Only hitters or pitchers | `--filter-type pitcher` |
| `--filter-position` | Position substring match | `--filter-position SS` |

### Sorting & Limiting

| Flag | Description | Example |
|------|-------------|---------|
| `--sort` | Sort by stat (hr, ops, era, k_per_9, wrc_plus, sb, whip) | `--sort hr` |
| `--reverse` | Ascending order (default: descending) | `--sort hr --reverse` |
| `--limit N` | Return only top N results | `--limit 10` |

### Output Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Text (default) | `.txt` or stdout | Formatted report with hitter/pitcher sections |
| JSON | `.json` | Structured data with metadata and projections |
| CSV | `.csv` | Spreadsheet-friendly format |

### Usage Examples

```bash
# Find fast shortstops (25+ SB)
uv run python batch.py --input kbo_players.json \
  --filter-type hitter --filter-position SS --filter-sb 25 --sort sb

# Verbose mode (shows processing progress)
uv run python batch.py --input kbo_players.json --verbose
```

## Usage (Single Player)

### CLI Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `--type` | `hitter` or `pitcher` | Player type (default: `hitter`) |
| `--name` | string | Player name for display (default: `Player`) |
| `--age` | int | Player age at time of transition (default: `27`) |
| `--role` | `starter` or `reliever` | Pitcher role (default: `starter`) |

**Hitter stats:** `--avg`, `--obp`, `--slg`, `--ops`, `--hr`, `--sb`, `--k_rate`, `--bb_rate`, `--iso`, `--wrc_plus`

**Pitcher stats:** `--era`, `--k_per_9`, `--bb_per_9`, `--whip`, `--hr_per_9`, `--fip`, `--k_bb_ratio`, `--era_plus`

**Other flags:** `--multi` (multi-year), `--comps` (MLB player comps), `--lookup` (live KBO stats)

### JSON Input (Single Player)

For single-player batch processing, provide a JSON file:

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

### Live Lookup (Real 2026 Data)
```
$ uv run python kbo_to_mlb.py --lookup "Kang Baekho"
  📡 Fetched from: https://mykbostats.com/players/1694
  📊 KBO Stats (2026): .297 AVG, 4 HR, .814 OPS

  KBO → MLB Projection: Kang Baek-ho
  Batting Average............... 0.255
  OPS........................... 0.708
  Home Runs..................... 3
```

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
kbo_to_mlb.py                  # Core projection engine + CLI
├── factors.json               # Recalibrated conversion factors (loaded at runtime)
├── BATTER_FACTORS             # Conversion multipliers for hitters
├── PITCHER_FACTORS            # Conversion multipliers for pitchers
├── age_adjustment_factor()    # Age-based adjustment
├── role_adjustment()          # Role/skill-based adjustment
├── project_batter()           # Main hitter projection
├── project_pitcher()          # Main pitcher projection
├── print_projection()         # Pretty-print output
└── demo()                     # Built-in examples

batch.py                       # Batch processing pipeline
├── load_json() / load_csv()   # Input parsing (JSON or CSV)
├── classify_player()          # Auto-detect hitter vs pitcher
├── project_player()           # Single-player projection wrapper
├── filter_players()           # Apply stat threshold filters
├── sort_players()             # Sort by any projection stat
└── output_json/csv/text()     # Multiple output formats

kbo_fetcher.py                 # Live KBO stats fetcher (MyKBOStats.com)
├── fetch_player()             # Fetch stats for a single player
├── search_player()            # Search by name across all KBO teams
├── fetch_team()               # Fetch entire team roster
├── fetch_league_leaders()     # Get top players by stat
├── to_projection_input()      # Convert fetched stats → projection input
└── CLI: --search, --url, --id, --team, --leaders, --project

mlb_comps.py                   # MLB player comparison engine
├── find_comps()               # Find closest MLB comps for projected stats
├── format_comps()             # Pretty-print comp results
├── _REFERENCE_HITTERS         # 53 representative MLB hitter stat lines
└── _REFERENCE_PITCHERS        # 35 representative MLB pitcher stat lines
```

## Live KBO Stats Fetcher (`kbo_fetcher.py`)

Fetches current-season KBO player statistics from [MyKBOStats.com](https://mykbostats.com) using `cloudscraper` (to bypass Cloudflare) and `beautifulsoup4` for HTML parsing.

### Standalone Usage

```bash
# Search for a player
uv run python kbo_fetcher.py --search "Kang Baekho"

# Fetch by player ID
uv run python kbo_fetcher.py --id 1694

# Fetch by full URL
uv run python kbo_fetcher.py --url "https://mykbostats.com/players/1694-Kang-Baekho-Hanwha-Eagles"

# Fetch and also run MLB projection
uv run python kbo_fetcher.py --id 1694 --project

# Fetch an entire team
uv run python kbo_fetcher.py --team "LG Twins"

# Show league leaders (slow — fetches all players)
uv run python kbo_fetcher.py --leaders --stat hr --type hitter --limit 10

# Output as JSON
uv run python kbo_fetcher.py --id 1694 -o player_stats.json
```

### How It Works

1. **Player search**: Scrapes all 10 KBO team roster pages to build a player index (cached for 24 hours).
2. **Stat fetching**: Parses MyKBOStats player pages for season stats tables.
3. **Stat mapping**: Translates MyKBOStats columns to the projection tool's stat keys:
   - Hitters: BA→avg, OBP→obp, SLG→slg, OPS→ops, HR→hr, SB→sb, K%/BB%→k_rate/bb_rate, ISO calculated
   - Pitchers: ERA→era, WHIP→whip, K/9 BB/9 HR/9 calculated from raw IP and totals
4. **Projection**: `--project` flag auto-runs the MLB projection on fetched stats.

### Notes

- MyKBOStats is an unofficial fan site. Stats are scraped respectfully with caching and rate limiting.
- Advanced stats (wRC+, FIP, ERA+) are not available on MyKBOStats; use Statiz or manual entry for those.
- The first `--search` or `--lookup` call builds a player index (~30 seconds). Subsequent calls use the cache.

## MLB Player Comps (`mlb_comps.py`)

Finds the closest MLB player comparisons for a projected stat line using normalized Euclidean distance across stat vectors. Includes a reference database of 50+ hitters and 35+ pitchers covering the full spectrum from All-Stars to bench players.

### Usage

```bash
# Auto-run with any projection
uv run python kbo_to_mlb.py --lookup "Na Gyun-an" --comps
uv run python kbo_to_mlb.py --avg 0.310 --ops 0.950 --hr 35 --comps

# Standalone
uv run python mlb_comps.py --type hitter --avg 0.255 --hr 18 --sb 15
uv run python mlb_comps.py --type pitcher --era 3.50 --k-per-9 9.0 --whip 1.15
```

### Example Output

```
  MLB COMPS (HITTER)
  ───────────────────────────────────────────────────────
  🥇 Rafael Devers                 39.5% match
  🥈 Teoscar Hernandez             37.5% match
  🥉 Gunnar Henderson              35.9% match
  ───────────────────────────────────────────────────────
```

### How It Works

1. Each projected stat line is compared against a database of 2025 MLB regulars.
2. Stats are z-score normalized per column to handle different scales (AVG ~0.250 vs HR ~20).
3. Similarity = `1 / (1 + euclidean_distance)` between normalized vectors.
4. Top 3 closest matches returned with 0–100% similarity scores.

## Sample Data

`sample_kbo_players.json` and `sample_kbo_players.csv` contain 20 realistic KBO players (10 hitters, 10 pitchers) for testing the batch pipeline.

## Requirements

- Python 3.11+
- `uv` (for dependency management)

```bash
# Install dependencies
uv pip install -e .

# Or run directly with uv
uv run python kbo_to_mlb.py
```

**Dependencies:** pandas, numpy, cloudscraper, beautifulsoup4 (see `pyproject.toml`)

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
