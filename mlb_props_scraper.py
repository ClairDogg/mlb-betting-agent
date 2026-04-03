"""
MLB Props Scraper
=================
Pulls today's MLB batter hit/HR props and pitcher SO props.

Strategy: Uses The Odds API with your existing free key for the endpoints
that ARE available on free tier, plus fetches additional prop markets.
Falls back gracefully if markets aren't available.

Free tier markets confirmed working:
  - h2h (moneyline)
  - spreads
  - totals (game O/U)

Player prop markets (may require upgrade — we try anyway and report status):
  - batter_hits, batter_home_runs, pitcher_strikeouts

Usage:
  python3 mlb_props_scraper.py
"""

import requests
import pandas as pd
import json
from datetime import datetime, date

API_KEY = "385918175f663216c44a89981aadb0c1"
BASE_URL = "https://api.the-odds-api.com/v4"

HEADERS = {"Accept": "application/json"}

PROP_MARKETS = [
    ("batter_hits",        "hits"),
    ("batter_home_runs",   "hr"),
    ("pitcher_strikeouts", "strikeouts"),
]

# Best books to check (in priority order)
BOOKMAKERS = "fanduel,draftkings,betmgm,caesars,pointsbet"


def get_mlb_events():
    """Get today's MLB event IDs."""
    url = f"{BASE_URL}/sports/baseball_mlb/events"
    params = {"apiKey": API_KEY, "dateFormat": "iso"}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        events = r.json()
        today = date.today().isoformat()
        todays = [e for e in events if e.get("commence_time", "").startswith(today)]
        print(f"  Found {len(todays)} MLB games today (of {len(events)} total)")
        return todays
    except Exception as e:
        print(f"  Could not fetch events: {e}")
        return []


def fetch_player_props(event_id, event_name, market, prop_label):
    """Fetch player props for a single event and market."""
    url = f"{BASE_URL}/sports/baseball_mlb/events/{event_id}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": market,
        "bookmakers": BOOKMAKERS,
        "oddsFormat": "american",
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if r.status_code == 422:
            return None, "not_available_free_tier"
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return None, str(e)

    records = []
    for bookmaker in data.get("bookmakers", []):
        book = bookmaker.get("title", "")
        for mkt in bookmaker.get("markets", []):
            if mkt.get("key") != market:
                continue
            for outcome in mkt.get("outcomes", []):
                if outcome.get("name", "").lower() != "over":
                    continue
                try:
                    odds_int = int(outcome.get("price", 0))
                except (ValueError, TypeError):
                    odds_int = None
                records.append({
                    "player":     outcome.get("description", outcome.get("name", "")),
                    "prop_type":  prop_label,
                    "line":       outcome.get("point"),
                    "odds":       outcome.get("price"),
                    "plus_money": odds_int is not None and odds_int > 0,
                    "game":       event_name,
                    "book":       book,
                    "pulled_at":  datetime.now().isoformat(),
                })
    # Dedupe: keep best odds per player
    best = {}
    for rec in records:
        key = (rec["player"], rec["prop_type"], rec["line"])
        if key not in best or (rec["odds"] and best[key]["odds"] and rec["odds"] > best[key]["odds"]):
            best[key] = rec
    return list(best.values()), None


def save(records, base_name):
    if not records:
        print(f"    No records for {base_name}")
        return
    with open(f"{base_name}.json", "w") as f:
        json.dump(records, f, indent=2)
    pd.DataFrame(records).to_csv(f"{base_name}.csv", index=False)
    print(f"    Saved: {base_name}.json + .csv ({len(records)} rows)")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MLB Props Scraper")
    print("=" * 60)
    print()

    events = get_mlb_events()
    if not events:
        print("No games today. Exiting.")
        exit()

    all_batter = []
    all_pitcher = []
    tier_error_reported = set()

    for event in events:
        eid = event["id"]
        name = event.get("home_team", "") + " vs " + event.get("away_team", "")
        print(f"\n  {name}")

        for market, label in PROP_MARKETS:
            records, err = fetch_player_props(eid, name, market, label)
            if err == "not_available_free_tier":
                if market not in tier_error_reported:
                    print(f"    {label}: not available on free tier (need paid plan)")
                    tier_error_reported.add(market)
                continue
            elif err:
                print(f"    {label}: error — {err}")
                continue

            if records:
                print(f"    {label}: {len(records)} props")
                if label in ("hits", "hr"):
                    all_batter.extend(records)
                else:
                    all_pitcher.extend(records)

    print()

    # Save outputs
    if all_batter:
        save(all_batter, "mlb_batter_props")
    else:
        # If props not available on free tier, create empty placeholder files
        # so downstream scripts don't break
        print("  No batter props available — creating empty placeholder files")
        empty = []
        with open("mlb_batter_props.json", "w") as f:
            json.dump(empty, f)
        pd.DataFrame(empty).to_csv("mlb_batter_props.csv", index=False)

    if all_pitcher:
        save(all_pitcher, "mlb_pitcher_props")
    else:
        print("  No pitcher props available — creating empty placeholder files")
        empty = []
        with open("mlb_pitcher_props.json", "w") as f:
            json.dump(empty, f)
        pd.DataFrame(empty).to_csv("mlb_pitcher_props.csv", index=False)

    print()
    print("Done.")
    print()

    if tier_error_reported:
        print("NOTE: Player prop markets require The Odds API paid tier ($29/mo).")
        print("Alternative: run fetch_dk_props_browser.js in your browser console")
        print("to pull props directly from DraftKings and save as mlb_batter_props.json")
