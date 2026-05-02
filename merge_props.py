"""
merge_props.py
==============
Combines batter_splits.json (from mlb_stats_scraper.py)
with mlb_batter_props.json (from fetch_dk_props_browser.js or mlb_props_scraper.py)
into a single merged dataset ready for the batting_gems_agent.jsx scoring engine.

Outputs:
  - merged_batter_data.json   ← used by batting_gems_agent.jsx
  - merged_batter_data.csv    ← for quick inspection

Usage:
  python3 merge_props.py
"""

import json
import pandas as pd
from difflib import get_close_matches

# ── Load data ────────────────────────────────────────────────────────────────

def load_json(path, label):
    try:
        with open(path) as f:
            data = json.load(f)
        print(f"  Loaded {label}: {len(data)} records")
        return data
    except FileNotFoundError:
        print(f"  WARNING: {path} not found — {label} will be empty")
        return []
    except Exception as e:
        print(f"  ERROR loading {path}: {e}")
        return []


def normalize_name(name):
    """Lowercase, strip punctuation for fuzzy matching."""
    return name.lower().replace(".", "").replace("'", "").replace("-", " ").strip()


# ── Merge logic ──────────────────────────────────────────────────────────────

def merge(splits, props):
    """
    Join splits (keyed by player_name) with props (keyed by player).
    Uses fuzzy name matching to handle minor spelling differences.
    """
    if not splits:
        print("  No splits data — output will only contain prop data")
    if not props:
        print("  No props data — output will only contain splits data")

    # Build lookup: normalized_name -> splits record
    splits_lookup = {}
    for s in splits:
        key = normalize_name(s.get("player_name", ""))
        splits_lookup[key] = s

    splits_names = list(splits_lookup.keys())

    # Build lookup: normalized_name -> best prop record (prefer plus-money)
    props_lookup = {}
    for p in props:
        key = normalize_name(p.get("player", ""))
        if key not in props_lookup:
            props_lookup[key] = p
        else:
            # Keep the one with better (higher) odds
            existing_odds = props_lookup[key].get("odds") or -999
            new_odds = p.get("odds") or -999
            if new_odds > existing_odds:
                props_lookup[key] = p

    merged = []
    matched = 0
    unmatched_props = []

    for prop_name, prop in props_lookup.items():
        # Try exact match first
        split = splits_lookup.get(prop_name)

        # Fuzzy match if exact fails
        if split is None and splits_names:
            close = get_close_matches(prop_name, splits_names, n=1, cutoff=0.82)
            if close:
                split = splits_lookup[close[0]]

        record = {
            # Prop fields
            "player":       prop.get("player", ""),
            "prop_type":    prop.get("prop_type", ""),
            "line":         prop.get("line"),
            "odds":         prop.get("odds"),
            "plus_money":   prop.get("plus_money", False),
            "game":         prop.get("game", ""),
        }

        if split:
            matched += 1
            # Splits fields — used by scoring engine
            record.update({
                "bats":                 split.get("bats", ""),
                "pitcher_throws":       split.get("pitcher_throws", ""),
                "handedness_avg":       split.get("handedness_avg"),
                "handedness_ops":       split.get("handedness_ops"),
                "monthly_avg":          split.get("monthly_avg"),
                "monthly_ops":          split.get("monthly_ops"),
                "home_away":            split.get("home_away", ""),
                "home_away_avg":        split.get("home_away_avg"),
                "home_away_ops":        split.get("home_away_ops"),
                "park_factor":          split.get("park_factor"),
                "venue":                split.get("venue", ""),
                "bvp_avg":              split.get("bvp_avg"),
                "bvp_abs":              split.get("bvp_abs"),
                "team":                 split.get("team", ""),
                "has_splits":           True,
            })
        else:
            unmatched_props.append(prop.get("player", ""))
            record["has_splits"] = False

        merged.append(record)

    # Also include splits-only players (no prop line posted yet)
    prop_names_seen = set(normalize_name(p.get("player", "")) for p in props)
    splits_only = 0
    for split_name, split in splits_lookup.items():
        if split_name not in prop_names_seen:
            splits_only += 1
            merged.append({
                "player":       split.get("player_name", ""),
                "prop_type":    None,
                "line":         None,
                "odds":         None,
                "plus_money":   False,
                "game":         split.get("game", ""),
                "bats":                 split.get("bats", ""),
                "pitcher_throws":       split.get("pitcher_throws", ""),
                "handedness_avg":       split.get("handedness_avg"),
                "handedness_ops":       split.get("handedness_ops"),
                "monthly_avg":          split.get("monthly_avg"),
                "monthly_ops":          split.get("monthly_ops"),
                "home_away":            split.get("home_away", ""),
                "home_away_avg":        split.get("home_away_avg"),
                "home_away_ops":        split.get("home_away_ops"),
                "park_factor":          split.get("park_factor"),
                "venue":                split.get("venue", ""),
                "bvp_avg":              split.get("bvp_avg"),
                "bvp_abs":              split.get("bvp_abs"),
                "team":                 split.get("team", ""),
                "has_splits":           True,
            })

    print(f"  Props matched to splits: {matched} / {len(props_lookup)}")
    if unmatched_props:
        print(f"  Props with no splits match ({len(unmatched_props)}): {', '.join(unmatched_props[:10])}" +
              (" ..." if len(unmatched_props) > 10 else ""))
    print(f"  Splits-only players (no prop line): {splits_only}")
    print(f"  Total merged records: {len(merged)}")

    return merged


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Merge Props + Splits")
    print("=" * 60)
    print()

    splits = load_json("batter_splits.json", "batter splits")
    props   = load_json("mlb_batter_props.json", "batter props")

    print()
    merged = merge(splits, props)

    # Save
    with open("merged_batter_data.json", "w") as f:
        json.dump(merged, f, indent=2)
    pd.DataFrame(merged).to_csv("merged_batter_data.csv", index=False)

    print()
    print("Saved: merged_batter_data.json + merged_batter_data.csv")
    print()
    print("Next step: git add merged_batter_data.json && git commit -m 'Add merged data'")
    print("Then open batting_gems_agent.jsx in your browser to see live scores.")
