"""
MLB Odds Scraper
================
Pulls today's MLB betting lines from The Odds API (theoddsapi.com).

Fetches two markets:
  1. Game totals (Over/Under) — used by the O/U agent
  2. Batter props: home runs & hits (Over/Under) — used by the batting gems agent
  3. Pitcher strikeout props — used by the strikeout agent

Outputs:
  - mlb_game_odds.json   / mlb_game_odds.csv    (game O/U lines)
  - mlb_batter_props.json / mlb_batter_props.csv (HR + hit props per batter)
  - mlb_pitcher_props.json / mlb_pitcher_props.csv (SO props per pitcher)

Setup:
  1. Sign up free at https://the-odds-api.com — free tier = 500 requests/month
  2. Copy your API key and paste it below (or set env var ODDS_API_KEY)
  3. pip install requests pandas
  4. python mlb_odds_scraper.py

Free tier usage per run:
  - 1 request for game totals
  - 1 request for batter HR props
  - 1 request for batter hits props
  - 1 request for pitcher SO props
  Total: ~4 requests per day = ~120/month — well within the 500 free limit
"""

import os
import requests
import pandas as pd
import json
from datetime import datetime

# Load .env file if present (pip install python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — falls back to hardcoded key below

# ── Config ────────────────────────────────────────────────────────────────

API_KEY = os.environ.get("ODDS_API_KEY", "385918175f663216c44a89981aadb0c1")
BASE    = "https://api.the-odds-api.com/v4"
SPORT   = "baseball_mlb"

# Bookmakers to pull from (comma-separated). These are widely available in the US.
# Full list: https://the-odds-api.com/sports-odds-data/bookmaker-apis.html
BOOKMAKERS = "draftkings,fanduel,betmgm"

# ── Helpers ───────────────────────────────────────────────────────────────

def get(path, params):
    params["apiKey"] = API_KEY
    resp = requests.get(f"{BASE}{path}", params=params, timeout=15)
    # Log remaining quota from response headers
    remaining = resp.headers.get("x-requests-remaining", "?")
    used      = resp.headers.get("x-requests-used", "?")
    print(f"  API quota — used: {used}, remaining: {remaining}")
    resp.raise_for_status()
    return resp.json()


def save(records, base_name):
    if not records:
        print(f"  No records for {base_name}")
        return
    with open(f"{base_name}.json", "w") as f:
        json.dump(records, f, indent=2)
    pd.DataFrame(records).to_csv(f"{base_name}.csv", index=False)
    print(f"  Saved: {base_name}.json + {base_name}.csv ({len(records)} rows)")


# ── 1. Game Totals (Over/Under) ───────────────────────────────────────────

def fetch_game_totals():
    """
    Returns one record per game with the consensus Over/Under line and odds.
    Used by: O/U agent
    """
    print("Fetching game totals (O/U)...")
    data = get(f"/sports/{SPORT}/odds", {
        "regions":   "us",
        "markets":   "totals",
        "bookmakers": BOOKMAKERS,
        "oddsFormat": "american",
    })

    records = []
    for game in data:
        away = game.get("away_team", "")
        home = game.get("home_team", "")
        commence = game.get("commence_time", "")

        for bm in game.get("bookmakers", []):
            bm_name = bm.get("key", "")
            for market in bm.get("markets", []):
                if market.get("key") != "totals":
                    continue
                for outcome in market.get("outcomes", []):
                    records.append({
                        "game":       f"{away} @ {home}",
                        "away_team":  away,
                        "home_team":  home,
                        "commence":   commence,
                        "bookmaker":  bm_name,
                        "side":       outcome.get("name"),       # Over / Under
                        "line":       outcome.get("point"),      # e.g. 8.5
                        "odds":       outcome.get("price"),      # e.g. -110
                        "pulled_at":  datetime.now().isoformat(),
                    })

    save(records, "mlb_game_odds")
    return records


# ── 2. Batter Props: HR + Hits ────────────────────────────────────────────

def fetch_batter_props():
    """
    Returns one record per batter per prop type (HR, hits) with line and odds.
    Used by: batting gems agent
    """
    print("Fetching batter props (HR + hits)...")
    records = []

    for market in ["batter_home_runs", "batter_hits"]:
        print(f"  market: {market}")
        try:
            data = get(f"/sports/{SPORT}/events", {"dateFormat": "iso"})
        except Exception as e:
            print(f"  Could not fetch event list: {e}")
            break

        # Fetch props event by event to stay within free tier limits
        # For paid tiers you can use /sports/{sport}/odds with player_props markets
        # Free tier approach: use the bulk player props endpoint
        try:
            prop_data = get(f"/sports/{SPORT}/odds", {
                "regions":    "us",
                "markets":    market,
                "bookmakers": BOOKMAKERS,
                "oddsFormat": "american",
            })
        except requests.HTTPError as e:
            print(f"  {market} not available on free tier: {e}")
            continue

        prop_type = "hr" if "home_runs" in market else "hits"

        for game in prop_data:
            away = game.get("away_team", "")
            home = game.get("home_team", "")
            for bm in game.get("bookmakers", []):
                bm_name = bm.get("key", "")
                for mkt in bm.get("markets", []):
                    if mkt.get("key") != market:
                        continue
                    for outcome in mkt.get("outcomes", []):
                        price = outcome.get("price")
                        records.append({
                            "game":        f"{away} @ {home}",
                            "away_team":   away,
                            "home_team":   home,
                            "player":      outcome.get("description", outcome.get("name", "")),
                            "prop_type":   prop_type,
                            "side":        outcome.get("name"),   # Over / Under
                            "line":        outcome.get("point"),  # e.g. 0.5
                            "odds":        price,                 # e.g. +150
                            "plus_money":  isinstance(price, (int, float)) and price > 0,
                            "bookmaker":   bm_name,
                            "pulled_at":   datetime.now().isoformat(),
                        })

    save(records, "mlb_batter_props")
    return records


# ── 3. Pitcher Strikeout Props ────────────────────────────────────────────

def fetch_pitcher_props():
    """
    Returns one record per pitcher with SO line and odds.
    Used by: strikeout agent
    """
    print("Fetching pitcher SO props...")
    records = []

    try:
        prop_data = get(f"/sports/{SPORT}/odds", {
            "regions":    "us",
            "markets":    "pitcher_strikeouts",
            "bookmakers": BOOKMAKERS,
            "oddsFormat": "american",
        })
    except requests.HTTPError as e:
        print(f"  pitcher_strikeouts not available: {e}")
        return records

    for game in prop_data:
        away = game.get("away_team", "")
        home = game.get("home_team", "")
        for bm in game.get("bookmakers", []):
            bm_name = bm.get("key", "")
            for mkt in bm.get("markets", []):
                if mkt.get("key") != "pitcher_strikeouts":
                    continue
                for outcome in mkt.get("outcomes", []):
                    price = outcome.get("price")
                    records.append({
                        "game":       f"{away} @ {home}",
                        "away_team":  away,
                        "home_team":  home,
                        "pitcher":    outcome.get("description", outcome.get("name", "")),
                        "side":       outcome.get("name"),   # Over / Under
                        "line":       outcome.get("point"),  # e.g. 6.5
                        "odds":       price,                 # e.g. -120
                        "plus_money": isinstance(price, (int, float)) and price > 0,
                        "bookmaker":  bm_name,
                        "pulled_at":  datetime.now().isoformat(),
                    })

    save(records, "mlb_pitcher_props")
    return records


# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MLB Odds Scraper")
    print("=" * 60)

    if API_KEY == "YOUR_API_KEY_HERE":
        print()
        print("⚠️  No API key set.")
        print("   1. Sign up free at https://the-odds-api.com")
        print("   2. Replace YOUR_API_KEY_HERE in this file with your key")
        print("      OR set the environment variable: ODDS_API_KEY=your_key")
        print()
    else:
        print()
        fetch_game_totals()
        print()
        fetch_batter_props()
        print()
        fetch_pitcher_props()
        print()
        print("Done. Files saved to current directory.")
        print()
        print("Next step: merge with mlb_stats_scraper.py output")
        print("  - Match batter props by player name to batter_splits.json")
        print("  - Match pitcher props by pitcher name to today's starters")
        print("  - Feed combined data into the agents")
