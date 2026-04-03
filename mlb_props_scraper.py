"""
MLB Props Scraper (DraftKings)
==============================
Pulls today's MLB batter HR & hit props and pitcher SO props
directly from DraftKings' public sportsbook API — no API key required.

Outputs:
  - mlb_batter_props.json / mlb_batter_props.csv
  - mlb_pitcher_props.json / mlb_pitcher_props.csv

Usage:
  pip3 install requests pandas --user
  python3 mlb_props_scraper.py
"""

import requests
import pandas as pd
import json
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# DraftKings subcategory IDs for MLB props (these are stable)
# batter_hits = 1000, batter_home_runs = 1001, pitcher_strikeouts = 1002
DK_CATEGORIES = {
    "batter_hits":        {"category": 1000, "subcategory": 10015},
    "batter_home_runs":   {"category": 1000, "subcategory": 10016},
    "pitcher_strikeouts": {"category": 1000, "subcategory": 10019},
}


def get_event_ids():
    """Fetch today's MLB event IDs from DraftKings."""
    url = "https://sportsbook.draftkings.com//sites/US-SB/api/v5/eventgroups/84240?format=json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        events = []
        for eg in data.get("eventGroup", {}).get("offerCategories", []):
            for sub in eg.get("offerSubcategoryDescriptors", []):
                for offer in sub.get("offerSubcategory", {}).get("offers", []):
                    for o in offer:
                        eid = o.get("eventId")
                        if eid:
                            events.append(eid)
        return list(set(events))
    except Exception as e:
        print(f"  Could not fetch event IDs: {e}")
        return []


def fetch_props_by_category(category_id, subcategory_id, prop_label):
    """
    Fetch props for a given DraftKings subcategory across all MLB games.
    Returns a list of records.
    """
    url = (
        f"https://sportsbook.draftkings.com//sites/US-SB/api/v5/eventgroups/84240"
        f"/categories/{category_id}/subcategories/{subcategory_id}?format=json"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  {prop_label}: fetch error — {e}")
        return []

    records = []
    event_group = data.get("eventGroup", {})

    # Walk through offerCategories -> offerSubcategory -> offers
    for cat in event_group.get("offerCategories", []):
        for sub in cat.get("offerSubcategoryDescriptors", []):
            subcategory = sub.get("offerSubcategory", {})
            for offer_list in subcategory.get("offers", []):
                for offer in offer_list:
                    label = offer.get("label", "")
                    event_id = offer.get("eventId")
                    # Get event name (home @ away)
                    event_name = ""
                    for ev in event_group.get("events", []):
                        if ev.get("eventId") == event_id:
                            event_name = ev.get("name", "")
                            break

                    for outcome in offer.get("outcomes", []):
                        player = outcome.get("participant", outcome.get("label", ""))
                        line = outcome.get("line")
                        odds = outcome.get("oddsAmerican", "")
                        side = outcome.get("label", "")  # Over / Under
                        if not player or side.lower() != "over":
                            continue
                        try:
                            odds_int = int(odds)
                        except (ValueError, TypeError):
                            odds_int = None

                        records.append({
                            "player":      player,
                            "prop_type":   prop_label,
                            "line":        line,
                            "odds":        odds,
                            "plus_money":  odds_int is not None and odds_int > 0,
                            "game":        event_name,
                            "pulled_at":   datetime.now().isoformat(),
                        })
    return records


def save(records, base_name):
    if not records:
        print(f"  No records for {base_name}")
        return
    with open(f"{base_name}.json", "w") as f:
        json.dump(records, f, indent=2)
    pd.DataFrame(records).to_csv(f"{base_name}.csv", index=False)
    print(f"  Saved: {base_name}.json + {base_name}.csv ({len(records)} rows)")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MLB Props Scraper (DraftKings)")
    print("=" * 60)
    print()

    # Batter hits
    print("Fetching batter hit props...")
    hit_records = fetch_props_by_category(1000, 10015, "hits")
    save(hit_records, "mlb_batter_props_hits")

    # Batter home runs
    print("Fetching batter HR props...")
    hr_records = fetch_props_by_category(1000, 10016, "hr")
    save(hr_records, "mlb_batter_props_hr")

    # Combine batter props
    all_batter = hit_records + hr_records
    save(all_batter, "mlb_batter_props")

    # Pitcher strikeouts
    print("Fetching pitcher SO props...")
    so_records = fetch_props_by_category(1000, 10019, "strikeouts")
    save(so_records, "mlb_pitcher_props")

    print()
    print("Done.")
    print()
    print("Next step: run merge_props.py to combine with batter_splits.json")
