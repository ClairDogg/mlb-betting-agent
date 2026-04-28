#!/bin/bash
# Run each morning before games start.
# Usage: bash run_daily.sh
cd "$(dirname "$0")"

echo "=== MLB Hidden Gems — Daily Run ==="
echo ""

echo "Step 1: Fetching batter splits from MLB Stats API..."
python3 mlb_stats_scraper.py
echo ""

echo "Step 2: Merging props..."
echo "  (If you have DraftKings props, move mlb_batter_props.json here first.)"
echo "  (See fetch_dk_props_browser.js for instructions on getting props from DraftKings.)"
python3 merge_props.py
echo ""

echo "Step 3: Starting local server on http://localhost:8080"
echo "  Open that URL in your browser, then Ctrl+C here when done."
python3 -m http.server 8080
