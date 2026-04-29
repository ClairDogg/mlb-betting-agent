"""
MLB Pitcher Strikeout Scraper
=============================
Pulls today's probable starters and collects:
  1. Season K/9 and innings depth
  2. Last 3 starts K totals (recent form)
  3. Opposing team strikeout rate (as hitters)
  4. Park K factor

Outputs: pitcher_splits.json, pitcher_splits.csv

Usage:
  python3 mlb_pitcher_scraper.py
"""

import requests
import pandas as pd
import json
import time
from datetime import datetime, date

BASE = "https://statsapi.mlb.com/api/v1"


def get(path, params=None):
    url = f"{BASE}{path}"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    time.sleep(0.25)
    return resp.json()


def current_season():
    return datetime.now().year


# ── today's probable starters ───────────────────────────────────────────────

def get_todays_starters():
    today = date.today().strftime("%Y-%m-%d")
    data = get("/schedule", params={
        "sportId": 1, "date": today,
        "hydrate": "probablePitcher,venue,lineups"
    })

    starters = []
    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            venue     = game.get("venue", {}).get("name", "Unknown Venue")
            home      = game.get("teams", {}).get("home", {})
            away      = game.get("teams", {}).get("away", {})
            home_id   = home.get("team", {}).get("id")
            away_id   = away.get("team", {}).get("id")
            home_name = home.get("team", {}).get("name", "")
            away_name = away.get("team", {}).get("name", "")

            for pitcher_data, team_id, team_name, opp_id, opp_name, is_home in [
                (home.get("probablePitcher", {}), home_id, home_name, away_id, away_name, True),
                (away.get("probablePitcher", {}), away_id, away_name, home_id, home_name, False),
            ]:
                if not pitcher_data.get("id"):
                    continue
                starters.append({
                    "pitcher_id":    pitcher_data["id"],
                    "pitcher_name":  pitcher_data.get("fullName", "Unknown"),
                    "pitcher_hand":  pitcher_data.get("pitchHand", {}).get("code", "R"),
                    "team_id":       team_id,
                    "team_name":     team_name,
                    "opp_team_id":   opp_id,
                    "opp_team_name": opp_name,
                    "venue":         venue,
                    "is_home":       is_home,
                })
    return starters


# ── pitcher stat fetchers ────────────────────────────────────────────────────

def get_season_stats(pitcher_id, season):
    data = get(f"/people/{pitcher_id}/stats",
               params={"stats": "season", "group": "pitching",
                       "season": season, "sportId": 1})
    splits = data.get("stats", [{}])[0].get("splits", [])
    if not splits:
        return {}
    s  = splits[0].get("stat", {})
    ip = float(s.get("inningsPitched", 0) or 0)
    gs = int(s.get("gamesStarted", 0) or 0)
    so = int(s.get("strikeOuts", 0) or 0)
    return {
        "season_so":           so,
        "season_ip":           ip,
        "season_gs":           gs,
        "season_k9":           round(so / ip * 9, 2) if ip > 0 else 0,
        "season_ip_per_start": round(ip / gs, 1) if gs > 0 else 0,
        "season_era":          s.get("era", "-.--"),
        "season_whip":         s.get("whip", "-.--"),
    }


def get_recent_form(pitcher_id, season, n=3):
    data = get(f"/people/{pitcher_id}/stats",
               params={"stats": "gameLog", "group": "pitching",
                       "season": season, "sportId": 1})
    splits = data.get("stats", [{}])[0].get("splits", [])
    starts = [s for s in splits if s.get("stat", {}).get("gamesStarted", 0) == 1]
    starts.sort(key=lambda x: x.get("date", ""), reverse=True)
    recent = starts[:n]

    if not recent:
        return {"recent_avg_k": 0, "recent_avg_ip": 0, "recent_k_list": []}

    k_list  = [s["stat"].get("strikeOuts", 0) for s in recent]
    ip_list = [float(s["stat"].get("inningsPitched", 0) or 0) for s in recent]
    return {
        "recent_avg_k":  round(sum(k_list) / len(k_list), 1),
        "recent_avg_ip": round(sum(ip_list) / len(ip_list), 1),
        "recent_k_list": k_list,
    }


def get_opp_k_rate(team_id, season):
    data = get(f"/teams/{team_id}/stats",
               params={"stats": "season", "group": "hitting",
                       "season": season, "sportId": 1})
    splits = data.get("stats", [{}])[0].get("splits", [])
    if not splits:
        return {"opp_team_k_rate": 0, "opp_team_so": 0}
    s  = splits[0].get("stat", {})
    so = int(s.get("strikeOuts", 0) or 0)
    pa = int(s.get("plateAppearances", 1) or 1)
    return {
        "opp_team_so":     so,
        "opp_team_k_rate": round(so / pa * 100, 1),
    }


# ── park K factors ───────────────────────────────────────────────────────────
# Approximation — strikeout rates are less park-dependent than HR.
# Coors Field is the main outlier (thin air = fewer Ks).
PARK_K_FACTORS = {
    "Coors Field":              95,
    "Great American Ball Park": 103,
    "Fenway Park":              98,
    "Wrigley Field":            101,
    "American Family Field":    102,
    "Globe Life Field":         100,
    "Yankee Stadium":           101,
    "Truist Park":              100,
    "Oracle Park":              100,
    "Petco Park":               99,
    "loanDepot park":           100,
    "T-Mobile Park":            100,
    "Kauffman Stadium":         99,
    "Oakland Coliseum":         100,
    "Progressive Field":        100,
    "Minute Maid Park":         101,
    "Target Field":             99,
    "Camden Yards":             100,
    "Busch Stadium":            100,
    "Guaranteed Rate Field":    101,
    "PNC Park":                 99,
    "Nationals Park":           100,
    "Tropicana Field":          101,
    "Rogers Centre":            100,
    "Angel Stadium":            100,
    "Chase Field":              101,
    "Dodger Stadium":           100,
    "Citi Field":               101,
    "Citizens Bank Park":       101,
    "Comerica Park":            99,
}


def get_park_k_factor(venue):
    return PARK_K_FACTORS.get(venue, 100)


# ── main build ───────────────────────────────────────────────────────────────

def build_pitcher_dataset(season=None):
    season = season or current_season()
    print(f"Season: {season}")

    print("Fetching today's probable starters...")
    starters = get_todays_starters()
    print(f"  {len(starters)} probable starters found")

    records = []
    for s in starters:
        pid  = s["pitcher_id"]
        name = s["pitcher_name"]
        print(f"  {name}...")

        record = {
            **s,
            "season":         season,
            "pulled_at":      datetime.now().isoformat(),
            "park_k_factor":  get_park_k_factor(s["venue"]),
            "k_line":         None,
            "k_odds":         None,
        }

        try:
            record.update(get_season_stats(pid, season))
        except Exception as e:
            print(f"    season stats error for {name}: {e}")

        try:
            record.update(get_recent_form(pid, season))
        except Exception as e:
            print(f"    recent form error for {name}: {e}")

        try:
            record.update(get_opp_k_rate(s["opp_team_id"], season))
        except Exception as e:
            print(f"    opp K rate error for {name}: {e}")

        records.append(record)

    print(f"\nTotal starters: {len(records)}")
    return records


def save_outputs(records):
    if not records:
        print("No starters found.")
        return

    with open("pitcher_splits.json", "w") as f:
        json.dump(records, f, indent=2)
    print("Saved: pitcher_splits.json")

    df = pd.DataFrame(records)
    df.to_csv("pitcher_splits.csv", index=False)
    print("Saved: pitcher_splits.csv")
    return df


if __name__ == "__main__":
    print("=" * 60)
    print("MLB Pitcher Strikeout Scraper")
    print("=" * 60)
    print()
    records = build_pitcher_dataset()
    df = save_outputs(records)

    if df is not None:
        print()
        print("Sample output:")
        cols = ["pitcher_name", "team_name", "opp_team_name", "venue",
                "season_k9", "season_ip_per_start", "season_era",
                "recent_avg_k", "recent_k_list", "opp_team_k_rate"]
        existing = [c for c in cols if c in df.columns]
        print(df[existing].to_string(index=False))
