"""
MLB Hidden Gems Scraper
=======================
Pulls batter split data from the free MLB Stats API and outputs:
  - batter_splits.json  (for the agent to consume)
  - batter_splits.csv   (for manual review in Excel)

Factors collected per batter:
  1. Handedness splits  (vs LHP / vs RHP)
  2. Monthly splits     (Apr–Oct)
  3. Home vs Away splits
  4. Batter vs Pitcher  (head-to-head history)

Usage:
  pip install requests pandas
  python mlb_scraper.py

Outputs land in the same directory as the script.
No API key required — MLB Stats API is free.
"""

import requests
import pandas as pd
import json
import time
from datetime import datetime, date

BASE = "https://statsapi.mlb.com/api/v1"

# ── helpers ────────────────────────────────────────────────────────────────

def get(path, params=None):
    """Safe GET with a small backoff to avoid hammering the API."""
    url = f"{BASE}{path}"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    time.sleep(0.25)          # be polite
    return resp.json()


def current_season():
    return datetime.now().year


# ── roster helpers ──────────────────────────────────────────────────────────

def get_all_teams():
    data = get("/teams", params={"sportId": 1})
    return {t["id"]: t["name"] for t in data["teams"]}


def get_roster(team_id, season):
    data = get(f"/teams/{team_id}/roster",
               params={"rosterType": "active", "season": season})
    return [
        p["person"] for p in data.get("roster", [])
        if p.get("position", {}).get("type") != "Pitcher"
    ]


# ── split fetchers ──────────────────────────────────────────────────────────

def get_handedness_splits(player_id, season):
    """Returns vs_lhp and vs_rhp hitting stats."""
    data2 = get(f"/people/{player_id}/stats",
                params={"stats": "statSplits",
                        "group": "hitting",
                        "gameType": "R",
                        "season": season,
                        "sitCodes": "vl,vr"})

    splits = {}
    for split in data2.get("stats", [{}])[0].get("splits", []):
        code = split.get("split", {}).get("code", "")
        s = split.get("stat", {})
        if code == "vl":
            splits["vs_lhp_avg"] = s.get("avg", ".000")
            splits["vs_lhp_hr"]  = s.get("homeRuns", 0)
            splits["vs_lhp_h"]   = s.get("hits", 0)
            splits["vs_lhp_ab"]  = s.get("atBats", 0)
        elif code == "vr":
            splits["vs_rhp_avg"] = s.get("avg", ".000")
            splits["vs_rhp_hr"]  = s.get("homeRuns", 0)
            splits["vs_rhp_h"]   = s.get("hits", 0)
            splits["vs_rhp_ab"]  = s.get("atBats", 0)
    return splits


def get_monthly_splits(player_id, season):
    """Returns a dict of month_name → {avg, hr, hits}."""
    data = get(f"/people/{player_id}/stats",
               params={"stats": "statSplits",
                       "group": "hitting",
                       "gameType": "R",
                       "season": season,
                       "sitCodes": "m4,m5,m6,m7,m8,m9,m10"})
    month_map = {
        "m4": "Apr", "m5": "May", "m6": "Jun",
        "m7": "Jul", "m8": "Aug", "m9": "Sep", "m10": "Oct"
    }
    result = {}
    for split in data.get("stats", [{}])[0].get("splits", []):
        code = split.get("split", {}).get("code", "")
        month = month_map.get(code)
        if month:
            s = split.get("stat", {})
            result[f"{month}_avg"] = s.get("avg", ".000")
            result[f"{month}_hr"]  = s.get("homeRuns", 0)
            result[f"{month}_h"]   = s.get("hits", 0)
    return result


def get_home_away_splits(player_id, season):
    """Returns home and away hitting stats."""
    data = get(f"/people/{player_id}/stats",
               params={"stats": "statSplits",
                       "group": "hitting",
                       "gameType": "R",
                       "season": season,
                       "sitCodes": "h,a"})
    result = {}
    for split in data.get("stats", [{}])[0].get("splits", []):
        code = split.get("split", {}).get("code", "")
        s = split.get("stat", {})
        if code == "h":
            result["home_avg"] = s.get("avg", ".000")
            result["home_hr"]  = s.get("homeRuns", 0)
            result["home_h"]   = s.get("hits", 0)
        elif code == "a":
            result["away_avg"] = s.get("avg", ".000")
            result["away_hr"]  = s.get("homeRuns", 0)
            result["away_h"]   = s.get("hits", 0)
    return result


def get_batter_vs_pitcher(batter_id, pitcher_id, season):
    """Returns head-to-head stats for a specific matchup."""
    data = get(f"/people/{batter_id}/stats",
               params={"stats": "vsPlayer",
                       "group": "hitting",
                       "opposingPlayerId": pitcher_id,
                       "season": season,
                       "sportId": 1})
    splits = data.get("stats", [{}])[0].get("splits", [])
    if not splits:
        return {"bvp_ab": 0, "bvp_avg": ".000", "bvp_hr": 0, "bvp_h": 0}
    s = splits[0].get("stat", {})
    return {
        "bvp_ab":  s.get("atBats", 0),
        "bvp_avg": s.get("avg", ".000"),
        "bvp_hr":  s.get("homeRuns", 0),
        "bvp_h":   s.get("hits", 0),
    }


# ── park factors (static lookup, updated each offseason) ───────────────────
# Source: Fangraphs park factors (5yr avg). 100 = neutral.
# HR factor above 105 = hitter-friendly for power.
PARK_FACTORS = {
    "Coors Field":                      {"hr": 131, "hits": 115},
    "Great American Ball Park":         {"hr": 118, "hits": 107},
    "Fenway Park":                      {"hr": 108, "hits": 110},
    "Wrigley Field":                    {"hr": 106, "hits": 103},
    "American Family Field":            {"hr": 112, "hits": 105},
    "Globe Life Field":                 {"hr": 104, "hits": 102},
    "Yankee Stadium":                   {"hr": 109, "hits": 101},
    "Truist Park":                      {"hr": 102, "hits": 100},
    "Oracle Park":                      {"hr": 85,  "hits": 95},
    "Petco Park":                       {"hr": 87,  "hits": 94},
    "loanDepot park":                   {"hr": 89,  "hits": 96},
    "T-Mobile Park":                    {"hr": 91,  "hits": 97},
    "Kauffman Stadium":                 {"hr": 93,  "hits": 98},
    "Oakland Coliseum":                 {"hr": 90,  "hits": 96},
    "Progressive Field":                {"hr": 97,  "hits": 99},
    "Minute Maid Park":                 {"hr": 100, "hits": 100},
    "Target Field":                     {"hr": 96,  "hits": 98},
    "Camden Yards":                     {"hr": 105, "hits": 103},
    "Busch Stadium":                    {"hr": 94,  "hits": 99},
    "Guaranteed Rate Field":            {"hr": 103, "hits": 101},
    "PNC Park":                         {"hr": 95,  "hits": 98},
    "Nationals Park":                   {"hr": 101, "hits": 100},
    "Tropicana Field":                  {"hr": 97,  "hits": 99},
    "Rogers Centre":                    {"hr": 107, "hits": 104},
    "Angel Stadium":                    {"hr": 96,  "hits": 99},
    "Chase Field":                      {"hr": 108, "hits": 104},
    "Dodger Stadium":                   {"hr": 99,  "hits": 100},
    "Citi Field":                       {"hr": 93,  "hits": 97},
    "Citizens Bank Park":               {"hr": 109, "hits": 104},
    "Comerica Park":                    {"hr": 95,  "hits": 98},
}


def get_park_factor(venue_name):
    return PARK_FACTORS.get(venue_name, {"hr": 100, "hits": 100})


# ── today's schedule ────────────────────────────────────────────────────────

def get_todays_games():
    today = date.today().strftime("%Y-%m-%d")
    data = get("/schedule",
               params={"sportId": 1, "date": today,
                       "hydrate": "probablePitcher,venue,lineups"})
    games = []
    for date_entry in data.get("dates", []):
        for g in date_entry.get("games", []):
            games.append(g)
    return games


def extract_game_info(game):
    """Pull venue, probable pitchers, and team IDs from a schedule entry."""
    venue = game.get("venue", {}).get("name", "Unknown Venue")
    home_team = game.get("teams", {}).get("home", {})
    away_team = game.get("teams", {}).get("away", {})
    home_pitcher = home_team.get("probablePitcher", {})
    away_pitcher = away_team.get("probablePitcher", {})

    return {
        "game_pk":          game.get("gamePk"),
        "venue":            venue,
        "home_team_id":     home_team.get("team", {}).get("id"),
        "home_team_name":   home_team.get("team", {}).get("name", "Home"),
        "away_team_id":     away_team.get("team", {}).get("id"),
        "away_team_name":   away_team.get("team", {}).get("name", "Away"),
        "home_pitcher_id":  home_pitcher.get("id"),
        "home_pitcher_name":home_pitcher.get("fullName", "TBD"),
        "home_pitcher_hand":home_pitcher.get("pitchHand", {}).get("code", "R"),
        "away_pitcher_id":  away_pitcher.get("id"),
        "away_pitcher_name":away_pitcher.get("fullName", "TBD"),
        "away_pitcher_hand":away_pitcher.get("pitchHand", {}).get("code", "R"),
        "park_hr_factor":   get_park_factor(venue)["hr"],
        "park_hit_factor":  get_park_factor(venue)["hits"],
    }


# ── main build ──────────────────────────────────────────────────────────────

def build_batter_dataset(season=None, max_players_per_team=None):
    """
    Full pipeline:
      - Fetch today's games → extract pitchers + venues
      - For each active roster batter, pull all four split types
      - Merge into a flat record per batter
      - Output JSON + CSV

    max_players_per_team: set a small int (e.g. 5) for a quick test run.
    """
    season = season or current_season()
    print(f"Season: {season}")

    print("Fetching today's games...")
    games = get_todays_games()
    game_infos = [extract_game_info(g) for g in games]
    print(f"  {len(game_infos)} games today")

    # Build a lookup: team_id → game info (for park/pitcher context)
    team_game_map = {}
    for gi in game_infos:
        team_game_map[gi["home_team_id"]] = {**gi, "is_home": True,
            "opp_pitcher_id":   gi["away_pitcher_id"],
            "opp_pitcher_name": gi["away_pitcher_name"],
            "opp_pitcher_hand": gi["away_pitcher_hand"]}
        team_game_map[gi["away_team_id"]] = {**gi, "is_home": False,
            "opp_pitcher_id":   gi["home_pitcher_id"],
            "opp_pitcher_name": gi["home_pitcher_name"],
            "opp_pitcher_hand": gi["home_pitcher_hand"]}

    print("Fetching team rosters...")
    teams = get_all_teams()
    all_records = []

    for team_id, team_name in teams.items():
        if team_id not in team_game_map:
            continue          # team not playing today

        gi = team_game_map[team_id]
        print(f"  {team_name}...")

        try:
            roster = get_roster(team_id, season)
        except Exception as e:
            print(f"    roster error: {e}")
            continue

        batters_processed = 0
        for player in roster:
            pid = player.get("id")
            pname = player.get("fullName", "Unknown")

            if max_players_per_team and batters_processed >= max_players_per_team:
                break

            record = {
                "player_id":        pid,
                "player_name":      pname,
                "team_id":          team_id,
                "team_name":        team_name,
                "venue":            gi["venue"],
                "park_hr_factor":   gi["park_hr_factor"],
                "park_hit_factor":  gi["park_hit_factor"],
                "is_home":          gi["is_home"],
                "opp_pitcher_id":   gi["opp_pitcher_id"],
                "opp_pitcher_name": gi["opp_pitcher_name"],
                "opp_pitcher_hand": gi["opp_pitcher_hand"],
                "season":           season,
                "pulled_at":        datetime.now().isoformat(),
            }

            try:
                record.update(get_handedness_splits(pid, season))
            except Exception as e:
                print(f"    handedness error for {pname}: {e}")

            try:
                record.update(get_monthly_splits(pid, season))
            except Exception as e:
                print(f"    monthly error for {pname}: {e}")

            try:
                record.update(get_home_away_splits(pid, season))
            except Exception as e:
                print(f"    home/away error for {pname}: {e}")

            if gi.get("opp_pitcher_id"):
                try:
                    record.update(get_batter_vs_pitcher(pid, gi["opp_pitcher_id"], season))
                except Exception as e:
                    print(f"    bvp error for {pname}: {e}")

            all_records.append(record)
            batters_processed += 1

    print(f"\nTotal records: {len(all_records)}")
    return all_records


def save_outputs(records):
    if not records:
        print("No records to save.")
        return

    # JSON
    with open("batter_splits.json", "w") as f:
        json.dump(records, f, indent=2)
    print("Saved: batter_splits.json")

    # CSV
    df = pd.DataFrame(records)
    df.to_csv("batter_splits.csv", index=False)
    print("Saved: batter_splits.csv")

    return df


# ── run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MLB Hidden Gems Scraper")
    print("=" * 60)
    print()

    # For a quick smoke-test, set max_players_per_team=3
    # Remove the argument (or set None) for full rosters
    records = build_batter_dataset(max_players_per_team=None)
    df = save_outputs(records)

    if df is not None:
        print()
        print("Sample output:")
        cols = ["player_name", "team_name", "venue",
                "vs_lhp_avg", "vs_rhp_avg",
                "home_avg", "away_avg",
                "Aug_avg", "park_hr_factor",
                "opp_pitcher_name", "opp_pitcher_hand",
                "bvp_avg", "bvp_ab"]
        existing = [c for c in cols if c in df.columns]
        print(df[existing].head(10).to_string(index=False))
