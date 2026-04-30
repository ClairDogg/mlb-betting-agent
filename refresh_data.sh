#!/bin/bash
# Pulls fresh MLB data every morning — runs automatically via cron.
# Does NOT start the server. Open http://localhost:8080 manually after this runs.
cd "$(dirname "$0")"
LOG=~/mlb-betting-agent/refresh.log

echo "=== $(date) ===" >> "$LOG"
python3 mlb_stats_scraper.py   >> "$LOG" 2>&1
python3 mlb_pitcher_scraper.py >> "$LOG" 2>&1
python3 mlb_props_scraper.py   >> "$LOG" 2>&1
python3 merge_props.py         >> "$LOG" 2>&1
echo "Done." >> "$LOG"
