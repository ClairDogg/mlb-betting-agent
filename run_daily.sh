#!/bin/bash
# Run each morning before games start.
# Usage: bash run_daily.sh
cd "$(dirname "$0")"

echo "=== MLB Hidden Gems — Daily Run ==="
echo ""

echo "Step 1: Fetching batter splits from MLB Stats API..."
python3 mlb_stats_scraper.py
echo ""

echo "Step 2: Fetching pitcher stats..."
python3 mlb_pitcher_scraper.py
echo ""

echo "Step 3: Fetching DraftKings props..."
python3 mlb_props_scraper.py
echo ""

echo "Step 4: Merging props with batter splits..."
python3 merge_props.py
echo ""

echo "Step 5: Starting local server on http://localhost:8080"
echo "  Open that URL in your browser, then Ctrl+C here when done."
python3 -m http.server 8080
