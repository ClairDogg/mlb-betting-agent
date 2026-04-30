"""
MLB Props Scraper
=================
Fetches today's DraftKings player prop odds from The Odds API (free tier).
Uses the per-event endpoint which works on the free plan.

Outputs:
  mlb_batter_props.json  — hit and HR over lines + odds per batter
  mlb_pitcher_props.json — strikeout over lines + odds per pitcher

API key: free tier, 500 requests/month.
Each daily run uses ~25 requests (one per game).

Usage:
  python3 mlb_props_scraper.py
"""

import requests
import json
import time
from datetime import datetime

API_KEY = "385918175f663216c44a89981aadb0c1"
BASE    = "https://api.the-odds-api.com/v4"


def get_todays_events():
    r = requests.get(f"{BASE}/sports/baseball_mlb/events",
                     params={"apiKey": API_KEY, "dateFormat": "iso"},
                     timeout=15)
    r.raise_for_status()
    print(f"  Requests remaining: {r.headers.get('x-requests-remaining', '?')}")
    return r.json()


def get_event_props(event_id):
    # DraftKings: hits + strikeouts | BetRivers: HR props
    # Fetch both and merge — no single bookmaker covers all three markets
    results = []
    for bookmaker, markets in [
        ("draftkings", "batter_hits,pitcher_strikeouts"),
        ("betrivers",  "batter_home_runs"),
    ]:
        r = requests.get(f"{BASE}/sports/baseball_mlb/events/{event_id}/odds",
                         params={
                             "apiKey":     API_KEY,
                             "regions":    "us",
                             "markets":    markets,
                             "oddsFormat": "american",
                             "bookmakers": bookmaker,
                         },
                         timeout=15)
        if r.status_code == 422:
            continue
        r.raise_for_status()
        time.sleep(0.3)
        results.append(r.json())

    if not results:
        return None

    # Merge bookmaker data into the first result
    merged = results[0]
    for extra in results[1:]:
        merged.setdefault("bookmakers", []).extend(extra.get("bookmakers", []))
    return merged


def parse_props(events_data):
    """Parse all events into flat batter and pitcher prop dicts keyed by player name."""
    batters  = {}  # name → {hr_line, hr_odds, hit_line, hit_odds}
    pitchers = {}  # name → {k_line, k_odds}

    for event in events_data:
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        for market in [m for bk in bookmakers for m in bk.get("markets", [])]:
            key = market["key"]
            for outcome in market.get("outcomes", []):
                if outcome.get("name") != "Over":
                    continue
                player = outcome.get("description", "").strip()
                if not player:
                    continue
                price = outcome.get("price", 0)
                point = outcome.get("point")
                odds  = f"+{price}" if price > 0 else str(price)

                if key == "batter_hits":
                    if player not in batters:
                        batters[player] = {}
                    batters[player]["hit_line"] = point
                    batters[player]["hit_odds"] = odds

                elif key == "batter_home_runs":
                    if player not in batters:
                        batters[player] = {}
                    batters[player]["hr_line"] = point
                    batters[player]["hr_odds"] = odds

                elif key == "pitcher_strikeouts":
                    if player not in pitchers:
                        pitchers[player] = {}
                    pitchers[player]["k_line"] = point
                    pitchers[player]["k_odds"] = odds

    batter_records  = [{"player_name": k, **v} for k, v in batters.items()]
    pitcher_records = [{"player_name": k, **v} for k, v in pitchers.items()]
    return batter_records, pitcher_records


def run():
    print("Fetching today's MLB events...")
    events = get_todays_events()
    print(f"  {len(events)} games found")

    print("Fetching player props for each game...")
    enriched = []
    for ev in events:
        matchup = f"{ev.get('away_team')} @ {ev.get('home_team')}"
        print(f"  {matchup}...")
        data = get_event_props(ev["id"])
        if data:
            enriched.append(data)

    batters, pitchers = parse_props(enriched)
    print(f"\n  {len(batters)} batter props, {len(pitchers)} pitcher props found")

    with open("mlb_batter_props.json", "w") as f:
        json.dump(batters, f, indent=2)
    print("Saved: mlb_batter_props.json")

    with open("mlb_pitcher_props.json", "w") as f:
        json.dump(pitchers, f, indent=2)
    print("Saved: mlb_pitcher_props.json")


if __name__ == "__main__":
    print("=" * 60)
    print("MLB Props Scraper")
    print("=" * 60)
    print()
    run()
