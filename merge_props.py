"""
Merges split data with DraftKings prop odds.
Uses fuzzy name matching (difflib) since MLB Stats API and Odds API
use slightly different name formats.

Outputs:
  merged_batter_data.json / .csv
  merged_pitcher_data.json / .csv
"""

import json
import difflib
import pandas as pd
from pathlib import Path

CUTOFF = 0.82


def load_json(path):
    p = Path(path)
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def build_index(records):
    index = {}
    for r in records:
        name = r.get("player_name", "").strip()
        if name:
            index[name] = r
    return index


def fuzzy_lookup(name, index):
    matches = difflib.get_close_matches(name, list(index.keys()), n=1, cutoff=CUTOFF)
    return index[matches[0]] if matches else None


def merge_batters():
    batters = load_json("batter_splits.json")
    props   = load_json("mlb_batter_props.json")

    if not batters:
        print("No data in batter_splits.json — run mlb_stats_scraper.py first.")
        return

    index     = build_index(props)
    has_props = bool(index)
    print(f"Batter props: {len(index)} entries loaded." if has_props else "No batter props found — odds will show as N/A.")

    merged, matched = [], 0
    for batter in batters:
        record = dict(batter)
        prop   = fuzzy_lookup(batter["player_name"], index) if has_props else None
        if prop:
            record["hr_line"]  = prop.get("hr_line")
            record["hr_odds"]  = prop.get("hr_odds")
            record["hit_line"] = prop.get("hit_line")
            record["hit_odds"] = prop.get("hit_odds")
            matched += 1
        else:
            record.setdefault("hr_line",  None)
            record.setdefault("hr_odds",  None)
            record.setdefault("hit_line", None)
            record.setdefault("hit_odds", None)
        merged.append(record)

    with open("merged_batter_data.json", "w") as f:
        json.dump(merged, f, indent=2)
    print(f"Saved: merged_batter_data.json  ({len(merged)} records, {matched} with props)")
    pd.DataFrame(merged).to_csv("merged_batter_data.csv", index=False)
    print("Saved: merged_batter_data.csv")


def merge_pitchers():
    pitchers = load_json("pitcher_splits.json")
    props    = load_json("mlb_pitcher_props.json")

    if not pitchers:
        print("No data in pitcher_splits.json — run mlb_pitcher_scraper.py first.")
        return

    index     = build_index(props)
    has_props = bool(index)
    print(f"Pitcher props: {len(index)} entries loaded." if has_props else "No pitcher props found — odds will show as N/A.")

    merged, matched = [], 0
    for pitcher in pitchers:
        record = dict(pitcher)
        prop   = fuzzy_lookup(pitcher["pitcher_name"], index) if has_props else None
        if prop:
            record["k_line"] = prop.get("k_line")
            record["k_odds"] = prop.get("k_odds")
            matched += 1
        else:
            record.setdefault("k_line", None)
            record.setdefault("k_odds", None)
        merged.append(record)

    with open("merged_pitcher_data.json", "w") as f:
        json.dump(merged, f, indent=2)
    print(f"Saved: merged_pitcher_data.json  ({len(merged)} records, {matched} with props)")
    pd.DataFrame(merged).to_csv("merged_pitcher_data.csv", index=False)
    print("Saved: merged_pitcher_data.csv")


if __name__ == "__main__":
    merge_batters()
    print()
    merge_pitchers()
