"""
Merges batter_splits.json with mlb_batter_props.json (DraftKings props).
If props are unavailable, passes through batter_splits.json with null odds fields
so downstream scripts and the HTML viewer don't break.

Uses fuzzy name matching (difflib) to join on player name, since MLB Stats API
and DraftKings use slightly different name formats.

Outputs: merged_batter_data.json, merged_batter_data.csv
"""

import json
import difflib
import pandas as pd
from pathlib import Path

BATTER_SPLITS = "batter_splits.json"
BATTER_PROPS  = "mlb_batter_props.json"
OUTPUT_JSON   = "merged_batter_data.json"
OUTPUT_CSV    = "merged_batter_data.csv"

CUTOFF = 0.82


def load_json(path):
    p = Path(path)
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def build_props_index(props):
    index = {}
    for p in props:
        name = p.get("player_name", "").strip()
        if name:
            index[name] = p
    return index


def fuzzy_lookup(name, index):
    candidates = list(index.keys())
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=CUTOFF)
    return index[matches[0]] if matches else None


def merge():
    batters = load_json(BATTER_SPLITS)
    props   = load_json(BATTER_PROPS)

    if not batters:
        print(f"No data in {BATTER_SPLITS} — run mlb_stats_scraper.py first.")
        return

    props_index = build_props_index(props)
    has_props   = bool(props_index)
    if not has_props:
        print("No props data found — odds will show as N/A in the viewer.")
    else:
        print(f"Loaded {len(props_index)} prop entries.")

    merged  = []
    matched = 0

    for batter in batters:
        record = dict(batter)
        prop   = fuzzy_lookup(batter["player_name"], props_index) if has_props else None

        if prop:
            record["hr_line"]  = prop.get("hr_line")
            record["hr_odds"]  = prop.get("hr_odds")
            record["hit_line"] = prop.get("hit_line")
            record["hit_odds"] = prop.get("hit_odds")
            matched += 1
        else:
            record["hr_line"]  = None
            record["hr_odds"]  = None
            record["hit_line"] = None
            record["hit_odds"] = None

        merged.append(record)

    with open(OUTPUT_JSON, "w") as f:
        json.dump(merged, f, indent=2)
    print(f"Saved: {OUTPUT_JSON}  ({len(merged)} records, {matched} with props)")

    df = pd.DataFrame(merged)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved: {OUTPUT_CSV}")


if __name__ == "__main__":
    merge()
