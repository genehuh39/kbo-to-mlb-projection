#!/usr/bin/env python3
"""
KBO Stats Fetcher

Fetches live KBO player statistics from MyKBOStats.com for use with the
KBO → MLB projection tool. Uses cloudscraper to bypass Cloudflare
anti-bot protection and BeautifulSoup for HTML parsing.

Usage:
    # Fetch a single player's stats by URL or player ID
    uv run python kbo_fetcher.py --url https://mykbostats.com/players/2290
    uv run python kbo_fetcher.py --id 2290

    # Search for a player by name
    uv run python kbo_fetcher.py --search "Kim Ha-seong"

    # Fetch an entire team's roster
    uv run python kbo_fetcher.py --team "LG Twins"
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urljoin

import cloudscraper
from bs4 import BeautifulSoup


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "https://mykbostats.com"
CACHE_DIR = Path(__file__).parent / ".cache" / "kbo_fetcher"
CACHE_TTL = 3600  # 1 hour cache for player pages

# Known team slugs for roster lookup
TEAM_SLUGS = {
    "lg twins": "6-LG-Twins",
    "kt wiz": "22-KT-Wiz",
    "ssg landers": "24-SSG-Landers",
    "samsung lions": "3-Samsung-Lions",
    "kia tigers": "5-Kia-Tigers",
    "nc dinos": "9-NC-Dinos",
    "hanwha eagles": "4-Hanwha-Eagles",
    "doosan bears": "1-Doosan-Bears",
    "kiwoom heroes": "23-Kiwoom-Heroes",
    "lotte giants": "2-Lotte-Giants",
}


# ============================================================================
# CACHE HELPERS
# ============================================================================

def _cache_path(url: str) -> Path:
    """Get cache file path for a URL."""
    import hashlib
    h = hashlib.md5(url.encode()).hexdigest()
    return CACHE_DIR / h


def _cached_get(scraper: cloudscraper.CloudScraper, url: str) -> str:
    """GET a URL with caching."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp = _cache_path(url)

    if cp.exists():
        age = time.time() - cp.stat().st_mtime
        if age < CACHE_TTL:
            return cp.read_text(encoding="utf-8")

    resp = scraper.get(url)
    resp.raise_for_status()
    cp.write_text(resp.text, encoding="utf-8")
    return resp.text


# ============================================================================
# HTML PARSING
# ============================================================================

def _parse_hitter_table(soup: BeautifulSoup) -> list[dict]:
    """
    Parse the season batting stats table from a MyKBOStats player page.

    Returns a list of dicts, one per season, with keys:
        year, team, avg, obp, slg, ops, g, pa, ab, r, h, hr, rbi,
        sb, cs, bb, so, tb, gdp, hbp, sh, sf, ibb, k_rate, bb_rate, iso
    """
    tables = soup.find_all("table")
    if not tables:
        return []

    # The first table is the season stats table
    table = tables[0]
    thead = table.find("thead")
    if not thead:
        return []

    header_cells = thead.find_all("th")
    headers = [h.get_text(strip=True) for h in header_cells]

    tbody = table.find("tbody")
    if not tbody:
        return []

    seasons = []
    for row in tbody.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        row_data = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                row_data[headers[i]] = cell.get_text(strip=True)

        # Skip "Career" row
        year_val = row_data.get("Year", "")
        if year_val.lower() == "career":
            continue

        season = _normalize_hitter_season(row_data)
        if season:
            seasons.append(season)

    return seasons


def _normalize_hitter_season(raw: dict) -> Optional[dict]:
    """Convert raw table row data to normalized stat dict."""
    try:
        year = int(raw.get("Year", ""))
    except (ValueError, TypeError):
        return None

    def _float(val):
        """Parse a stat value, handling empty strings and dashes."""
        if not val or val in ("-", "", ".000", "—"):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _int(val):
        f = _float(val)
        if f is not None:
            return int(f)
        return None

    avg = _float(raw.get("BA"))
    obp = _float(raw.get("OBP"))
    slg = _float(raw.get("SLG"))
    ops = _float(raw.get("OPS"))
    hr = _int(raw.get("HR"))
    sb = _int(raw.get("SB"))
    bb = _int(raw.get("BB"))
    so = _int(raw.get("SO"))
    pa = _int(raw.get("PA"))
    ab = _int(raw.get("AB"))
    h = _int(raw.get("H"))
    rbi = _int(raw.get("RBI"))
    g = _int(raw.get("G"))
    r = _int(raw.get("R"))
    cs = _int(raw.get("CS"))
    tb = _int(raw.get("TB"))
    gdp = _int(raw.get("GDP"))
    hbp = _int(raw.get("HBP"))
    sh = _int(raw.get("SH"))
    sf = _int(raw.get("SF"))
    ibb = _int(raw.get("IBB"))

    # Calculate derived stats
    k_rate = None
    bb_rate = None
    if pa and pa > 0:
        if so is not None:
            k_rate = round(so / pa, 4)
        if bb is not None:
            bb_rate = round(bb / pa, 4)

    iso = None
    if slg is not None and avg is not None:
        iso = round(slg - avg, 4)

    # MyKBOStats doesn't have wRC+, set to None
    wrc_plus = None

    return {
        "year": year,
        "team": raw.get("Team", ""),
        "avg": avg,
        "obp": obp,
        "slg": slg,
        "ops": ops,
        "hr": hr,
        "sb": sb,
        "k_rate": k_rate,
        "bb_rate": bb_rate,
        "iso": iso,
        "wrc_plus": wrc_plus,
        # Extended stats (not used by projection but useful)
        "g": g, "pa": pa, "ab": ab, "r": r,
        "h": h, "rbi": rbi, "cs": cs,
        "bb": bb, "so": so, "tb": tb,
        "gdp": gdp, "hbp": hbp, "sh": sh, "sf": sf, "ibb": ibb,
    }


def _parse_pitcher_table(soup: BeautifulSoup) -> list[dict]:
    """
    Parse the season pitching stats table from a MyKBOStats player page.

    Returns a list of dicts, one per season, with keys:
        year, team, era, whip, w, l, sv, g, gs, ip, r, er,
        h, hr, so, bb, ibb, hb, k_per_9, bb_per_9, hr_per_9, k_bb_ratio
    """
    tables = soup.find_all("table")
    if not tables:
        return []

    table = tables[0]
    thead = table.find("thead")
    if not thead:
        return []

    header_cells = thead.find_all("th")
    headers = [h.get_text(strip=True) for h in header_cells]

    tbody = table.find("tbody")
    if not tbody:
        return []

    seasons = []
    for row in tbody.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        row_data = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                row_data[headers[i]] = cell.get_text(strip=True)

        year_val = row_data.get("Year", "")
        if year_val.lower() == "career":
            continue

        season = _normalize_pitcher_season(row_data)
        if season:
            seasons.append(season)

    return seasons


def _normalize_pitcher_season(raw: dict) -> Optional[dict]:
    """Convert raw table row data to normalized pitcher stat dict."""
    try:
        year = int(raw.get("Year", ""))
    except (ValueError, TypeError):
        return None

    def _float(val):
        if not val or val in ("-", "", "—"):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _int(val):
        f = _float(val)
        if f is not None:
            return int(f)
        return None

    def _parse_ip(ip_str):
        """Parse IP like '27 ⅔' or '137 ⅓' or '6.0' into float."""
        if not ip_str:
            return None
        # Handle fraction format: "27 ⅔"
        ip_str = ip_str.strip()
        # Replace Unicode fraction characters
        ip_str = ip_str.replace("⅓", ".333").replace("⅔", ".667")
        # Handle "X Y/Z" format
        parts = ip_str.split()
        try:
            if len(parts) == 2:
                return float(parts[0]) + float(parts[1])
            return float(parts[0])
        except (ValueError, TypeError):
            return None

    era = _float(raw.get("ERA"))
    whip = _float(raw.get("WHIP"))
    w = _int(raw.get("W"))
    l = _int(raw.get("L"))
    sv = _int(raw.get("SV"))
    g = _int(raw.get("G"))
    gs = _int(raw.get("GS"))
    ip = _parse_ip(raw.get("IP"))
    r = _int(raw.get("R"))
    er = _int(raw.get("ER"))
    h = _int(raw.get("H"))
    hr = _int(raw.get("HR"))
    so = _int(raw.get("SO"))
    bb = _int(raw.get("BB"))
    ibb = _int(raw.get("IBB"))
    hb = _int(raw.get("HB"))

    # Calculate per-9 stats
    k_per_9 = None
    bb_per_9 = None
    hr_per_9 = None
    k_bb_ratio = None

    if ip and ip > 0:
        if so is not None:
            k_per_9 = round((so / ip) * 9, 2)
        if bb is not None:
            bb_per_9 = round((bb / ip) * 9, 2)
        if hr is not None:
            hr_per_9 = round((hr / ip) * 9, 2)
        if so is not None and bb is not None and bb > 0:
            k_bb_ratio = round(so / bb, 2)
        elif so is not None and bb is not None and bb == 0:
            k_bb_ratio = float('inf')

    # MyKBOStats doesn't have FIP or ERA+
    fip = None
    era_plus = None

    return {
        "year": year,
        "team": raw.get("Team", ""),
        "era": era,
        "whip": whip,
        "k_per_9": k_per_9,
        "bb_per_9": bb_per_9,
        "hr_per_9": hr_per_9,
        "k_bb_ratio": k_bb_ratio,
        "fip": fip,
        "era_plus": era_plus,
        # Extended stats
        "w": w, "l": l, "sv": sv,
        "g": g, "gs": gs, "ip": ip,
        "r": r, "er": er, "h": h, "hr": hr,
        "so": so, "bb": bb, "ibb": ibb, "hb": hb,
    }


def _parse_player_name(soup: BeautifulSoup) -> str:
    """Extract player name from page heading."""
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(strip=True)
        # Remove trailing team info like "KBO League Batting Stats - LG Twins"
        text = re.sub(r'\s*KBO League.*$', '', text)
        return text.strip()
    return "Unknown"


def _parse_player_position(soup: BeautifulSoup) -> str:
    """Try to determine position from page metadata or breadcrumbs."""
    # Look for position in the page title or meta
    title = soup.find("title")
    if title:
        title_text = title.get_text(strip=True)
        # Title format: "Name KBO League Batting Stats - Team | MyKBO Stats"
        # or: "Name KBO League Pitching Stats - Team | MyKBO Stats"
        return title_text
    return ""


def _detect_player_type(soup: BeautifulSoup) -> str:
    """
    Detect whether player page is for a hitter or pitcher.

    Returns "hitter" or "pitcher".
    """
    title = soup.find("title")
    if title:
        title_text = title.get_text(strip=True)
        if "Pitching" in title_text:
            return "pitcher"
    # Check table headers
    tables = soup.find_all("table")
    if tables:
        headers = [h.get_text(strip=True) for h in tables[0].find_all("th")]
        if "ERA" in headers:
            return "pitcher"
    return "hitter"


# ============================================================================
# PLAYER SEARCH / LOOKUP
# ============================================================================

def _scrape_team_roster(team_slug: str, scraper: cloudscraper.CloudScraper) -> list[dict]:
    """
    Scrape a team's roster page to build a player index.

    Returns list of dicts with: name, url, player_id
    """
    url = f"{BASE_URL}/teams/{team_slug}/roster"
    html = _cached_get(scraper, url)
    soup = BeautifulSoup(html, "html.parser")

    players = []
    seen_ids = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if re.search(r'/players/\d+', href):
            # Extract player ID
            pid_match = re.search(r'/players/(\d+)', href)
            player_id = pid_match.group(1) if pid_match else None
            if not player_id or player_id in seen_ids:
                continue
            seen_ids.add(player_id)

            name = link.get_text(strip=True)
            # Some player links use an image (empty text), grab from href slug
            if not name:
                slug_match = re.search(r'/players/\d+-(.+?)(?:-LG-Twins|-KT-Wiz|-SSG-Landers|-Samsung-Lions|-Kia-Tigers|-NC-Dinos|-Hanwha-Eagles|-Doosan-Bears|-Kiwoom-Heroes|-Lotte-Giants)?$', href)
                if slug_match:
                    name = slug_match.group(1).replace('-', ' ')
                else:
                    continue
            if name == "Foreign Players":
                continue
            full_url = urljoin(BASE_URL, href)
            players.append({
                "name": name,
                "url": full_url,
                "player_id": player_id,
                "team": team_slug.split("-", 1)[1].replace("-", " "),
            })

    return players


def search_player(name: str, scraper: Optional[cloudscraper.CloudScraper] = None) -> list[dict]:
    """
    Search for a KBO player by name across all teams.

    This scrapes team rosters and does fuzzy matching. Results are cached
    for subsequent lookups.

    Args:
        name: Player name to search for (partial match supported).
        scraper: Optional pre-configured CloudScraper instance.

    Returns:
        List of matching players with name, url, player_id, team.
    """
    if scraper is None:
        scraper = cloudscraper.create_scraper()

    name_lower = name.lower().strip()
    # Normalize: remove hyphens for fuzzy matching
    name_normalized = name_lower.replace("-", " ")
    name_parts = name_normalized.split()

    matches = []

    # Check cache first
    roster_cache = CACHE_DIR / "roster_index.json"
    all_players = []

    if roster_cache.exists():
        age = time.time() - roster_cache.stat().st_mtime
        if age < 86400:  # 24 hour cache
            try:
                all_players = json.loads(roster_cache.read_text())
            except (json.JSONDecodeError, IOError):
                pass

    # Build index if needed
    if not all_players:
        print("Building player index from team rosters...", file=sys.stderr)
        for team_name, slug in TEAM_SLUGS.items():
            try:
                team_players = _scrape_team_roster(slug, scraper)
                all_players.extend(team_players)
                time.sleep(0.5)  # Be polite
            except Exception as e:
                print(f"  Warning: Could not fetch {team_name}: {e}", file=sys.stderr)

        # Cache the index
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        roster_cache.write_text(json.dumps(all_players, indent=2))
        print(f"  Indexed {len(all_players)} players.", file=sys.stderr)

    # Fuzzy match
    for p in all_players:
        p_name_lower = p["name"].lower()
        p_name_normalized = p_name_lower.replace("-", " ")

        # Direct substring match (normalized)
        if name_normalized in p_name_normalized or p_name_normalized in name_normalized:
            matches.append(p)
        # All search terms must appear somewhere in the player name
        elif all(part in p_name_normalized for part in name_parts):
            matches.append(p)

    return matches


# ============================================================================
# MAIN FETCH FUNCTION
# ============================================================================

def fetch_player(
    url: Optional[str] = None,
    player_id: Optional[str] = None,
    season: Optional[int] = None,
    scraper: Optional[cloudscraper.CloudScraper] = None,
) -> dict:
    """
    Fetch KBO stats for a player from MyKBOStats.com.

    Args:
        url: Full URL to player page (e.g., https://mykbostats.com/players/2290).
        player_id: Numeric player ID (alternative to URL).
        season: Specific season to fetch (default: most recent).
        scraper: Optional pre-configured CloudScraper instance.

    Returns:
        Dict with keys:
            name, player_type, url, seasons (list of season stat dicts),
            current_stats (dict ready for projection tool).
    """
    if scraper is None:
        scraper = cloudscraper.create_scraper()

    if url:
        fetch_url = url
    elif player_id:
        fetch_url = f"{BASE_URL}/players/{player_id}"
    else:
        raise ValueError("Must provide either url or player_id")

    html = _cached_get(scraper, fetch_url)
    soup = BeautifulSoup(html, "html.parser")

    name = _parse_player_name(soup)
    player_type = _detect_player_type(soup)
    position = _parse_player_position(soup)

    if player_type == "hitter":
        seasons = _parse_hitter_table(soup)
    else:
        seasons = _parse_pitcher_table(soup)

    # Get the requested season or the most recent
    if season is not None:
        target = [s for s in seasons if s["year"] == season]
        current_stats = target[0] if target else (seasons[0] if seasons else {})
    else:
        current_stats = seasons[0] if seasons else {}

    # Build projection-ready stats dict
    proj_stats = {}
    for key in ("avg", "obp", "slg", "ops", "hr", "sb",
                 "k_rate", "bb_rate", "iso", "wrc_plus",
                 "era", "whip", "k_per_9", "bb_per_9",
                 "hr_per_9", "k_bb_ratio", "fip", "era_plus"):
        if key in current_stats and current_stats[key] is not None:
            proj_stats[key] = current_stats[key]

    return {
        "name": name,
        "player_type": player_type,
        "position_info": position,
        "url": fetch_url,
        "seasons": seasons,
        "current_stats": current_stats,
        "projection_stats": proj_stats,
    }


# ============================================================================
# TEAM FETCH
# ============================================================================

def fetch_team(team_name: str, season: Optional[int] = None) -> list[dict]:
    """
    Fetch stats for all players on a team.

    Args:
        team_name: Team name (e.g., "LG Twins", "Kia Tigers").
        season: Specific season (default: most recent).

    Returns:
        List of player result dicts from fetch_player().
    """
    scraper = cloudscraper.create_scraper()

    team_lower = team_name.lower().strip()
    slug = TEAM_SLUGS.get(team_lower)
    if not slug:
        # Try partial match
        for name, s in TEAM_SLUGS.items():
            if team_lower in name or name in team_lower:
                slug = s
                break

    if not slug:
        raise ValueError(f"Unknown team: {team_name}. Known: {list(TEAM_SLUGS.keys())}")

    players = _scrape_team_roster(slug, scraper)
    results = []

    for i, p in enumerate(players):
        try:
            result = fetch_player(url=p["url"], season=season, scraper=scraper)
            result["team"] = slug.split("-", 1)[1].replace("-", " ")
            results.append(result)
            if (i + 1) % 5 == 0:
                print(f"  Fetched {i + 1}/{len(players)}...", file=sys.stderr)
            time.sleep(0.3)  # Rate limiting
        except Exception as e:
            print(f"  Warning: Failed to fetch {p['name']}: {e}", file=sys.stderr)

    return results


# ============================================================================
# LEAGUE LEADERS
# ============================================================================

def fetch_league_leaders(
    stat: str = "hr",
    player_type: str = "hitter",
    limit: int = 10,
) -> list[dict]:
    """
    Fetch the top KBO players by a given stat.

    This scrapes all team rosters, fetches individual stats, and ranks them.

    Note: This is slow because it fetches every player. For quick lookups,
    use search_player() + fetch_player() instead.

    Args:
        stat: Stat to rank by ('hr', 'avg', 'ops', 'sb', 'era', 'k_per_9', 'whip').
        player_type: 'hitter' or 'pitcher'.
        limit: Maximum number of results.

    Returns:
        List of player result dicts, sorted by the requested stat.
    """
    scraper = cloudscraper.create_scraper()
    all_players_data = []

    # Build roster index if needed
    roster_cache = CACHE_DIR / "roster_index.json"
    all_players = []

    if roster_cache.exists():
        age = time.time() - roster_cache.stat().st_mtime
        if age < 86400:
            try:
                all_players = json.loads(roster_cache.read_text())
            except (json.JSONDecodeError, IOError):
                pass

    if not all_players:
        print("Building player index...", file=sys.stderr)
        for team_name, slug in TEAM_SLUGS.items():
            try:
                team_players = _scrape_team_roster(slug, scraper)
                all_players.extend(team_players)
                time.sleep(0.5)
            except Exception as e:
                print(f"  Warning: {team_name}: {e}", file=sys.stderr)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        roster_cache.write_text(json.dumps(all_players, indent=2))

    print(f"Fetching stats for {len(all_players)} players...", file=sys.stderr)

    for i, p in enumerate(all_players):
        try:
            result = fetch_player(url=p["url"], scraper=scraper)
            if result["player_type"] == player_type:
                stat_val = result["current_stats"].get(stat)
                if stat_val is not None:
                    all_players_data.append(result)
            if (i + 1) % 20 == 0:
                print(f"  Fetched {i + 1}/{len(all_players)}...", file=sys.stderr)
            time.sleep(0.2)
        except Exception as e:
            pass  # Skip failed fetches

    # Sort: descending for most stats, ascending for ERA/WHIP
    reverse = stat not in ("era", "whip")
    all_players_data.sort(
        key=lambda p: p["current_stats"].get(stat, 0) or 0,
        reverse=reverse,
    )

    return all_players_data[:limit]


# ============================================================================
# UTILITY: CONVERT TO PROJECTION INPUT
# ============================================================================

def to_projection_input(player_data: dict, age: Optional[int] = None) -> dict:
    """
    Convert fetch_player() output to input format for kbo_to_mlb.project_batter()
    or project_pitcher().

    Args:
        player_data: Result from fetch_player().
        age: Player age (will try to infer from available data if not provided).

    Returns:
        Dict with 'kbo_stats', 'age', 'player_type', 'name', 'role'.
    """
    result = {
        "name": player_data["name"],
        "player_type": player_data["player_type"],
        "age": age or 27,  # Default if unknown
        "kbo_stats": player_data["projection_stats"],
        "role": "starter",
    }

    # Try to determine role from position info
    pos_info = player_data.get("position_info", "").lower()
    if "relief" in pos_info or "reliever" in pos_info:
        result["role"] = "reliever"
    elif player_data["player_type"] == "pitcher":
        # Check games started vs total games
        cs = player_data.get("current_stats", {})
        gs = cs.get("gs", 0) or 0
        g = cs.get("g", 0) or 0
        if g > 0 and gs == 0:
            result["role"] = "reliever"

    return result


# ============================================================================
# CLI
# ============================================================================

def cli():
    parser = argparse.ArgumentParser(
        description="Fetch live KBO player statistics from MyKBOStats.com.",
    )

    parser.add_argument(
        "--url",
        help="Full URL to a MyKBOStats player page.",
    )
    parser.add_argument(
        "--id",
        help="Numeric player ID from MyKBOStats.",
    )
    parser.add_argument(
        "--search", "-s",
        help="Search for a player by name.",
    )
    parser.add_argument(
        "--team", "-t",
        help="Fetch entire team roster (e.g., 'LG Twins').",
    )
    parser.add_argument(
        "--leaders",
        action="store_true",
        help="Show league leaders.",
    )
    parser.add_argument(
        "--stat",
        default="hr",
        help="Stat to rank by for --leaders (default: hr).",
    )
    parser.add_argument(
        "--type",
        choices=["hitter", "pitcher"],
        default="hitter",
        help="Player type for --leaders (default: hitter).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit for --leaders (default: 10).",
    )
    parser.add_argument(
        "--season",
        type=int,
        help="Specific season to fetch (default: most recent).",
    )
    parser.add_argument(
        "--output", "-o",
        default="-",
        help="Output file (default: stdout). Use .json for JSON.",
    )
    parser.add_argument(
        "--project",
        action="store_true",
        help="Also run MLB projection on fetched stats.",
    )

    args = parser.parse_args()

    # --- Search mode ---
    if args.search:
        matches = search_player(args.search)
        if not matches:
            print(f"No players found matching '{args.search}'.")
            sys.exit(1)

        print(f"Found {len(matches)} player(s):")
        for i, m in enumerate(matches):
            print(f"  [{i}] {m['name']} ({m['team']}) — {m['url']}")

        if len(matches) == 1:
            # Auto-fetch if only one match
            result = fetch_player(url=matches[0]["url"], season=args.season)
            _output_result(result, args)
        else:
            print("\nUse --url or --id with one of the URLs above to fetch stats.")
        return

    # --- Team mode ---
    if args.team:
        results = fetch_team(args.team, season=args.season)
        _output_results(results, args)
        return

    # --- League leaders mode ---
    if args.leaders:
        results = fetch_league_leaders(
            stat=args.stat,
            player_type=args.type,
            limit=args.limit,
        )
        _output_results(results, args)
        return

    # --- Single player mode ---
    if args.url or args.id:
        result = fetch_player(url=args.url, player_id=args.id, season=args.season)
        _output_result(result, args)
        return

    parser.print_help()


def _output_result(result: dict, args):
    """Output a single player result."""
    if args.project:
        _run_projection(result)
        return

    output = {
        "name": result["name"],
        "player_type": result["player_type"],
        "url": result["url"],
        "current_season": result["current_stats"],
        "all_seasons": result["seasons"],
        "projection_input": result["projection_stats"],
    }

    if args.output == "-":
        print(json.dumps(output, indent=2, default=str))
    else:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2, default=str)


def _output_results(results: list[dict], args):
    """Output multiple player results."""
    if args.project:
        for r in results:
            _run_projection(r)
        return

    output = []
    for r in results:
        output.append({
            "name": r["name"],
            "player_type": r["player_type"],
            "url": r["url"],
            "current_season": r["current_stats"],
            "projection_input": r["projection_stats"],
        })

    if args.output == "-":
        print(json.dumps(output, indent=2, default=str))
    else:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2, default=str)


def _run_projection(player_data: dict):
    """Run MLB projection on a player's fetched stats."""
    from kbo_to_mlb import (
        project_batter,
        project_pitcher,
        print_projection,
    )

    proj_input = to_projection_input(player_data)
    stats = proj_input["kbo_stats"]
    name = proj_input["name"]
    age = proj_input["age"]

    if not stats:
        print(f"\n⚠ {name}: No stats available for projection.")
        return

    if proj_input["player_type"] == "hitter":
        proj = project_batter(stats, age=age)
        print_projection(proj, name, "hitter")
    else:
        proj = project_pitcher(stats, age=age, role=proj_input["role"])
        print_projection(proj, name, "pitcher")


if __name__ == "__main__":
    cli()
