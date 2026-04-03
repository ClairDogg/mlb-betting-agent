/**
 * fetch_dk_props_browser.js
 * =========================
 * Run this in Chrome DevTools console while on ANY page at:
 *   https://sportsbook.draftkings.com
 *
 * It fetches today's MLB batter hit/HR props and pitcher SO props,
 * then downloads them as mlb_batter_props.json and mlb_pitcher_props.json
 * into your Downloads folder.
 *
 * HOW TO USE:
 *   1. Open Chrome and go to https://sportsbook.draftkings.com
 *   2. Press F12 (or Cmd+Option+I on Mac) to open DevTools
 *   3. Click the "Console" tab
 *   4. Paste this entire script and press Enter
 *   5. Two JSON files will download automatically
 *   6. Move them into your mlb-betting-agent folder
 */

(async () => {
  const BASE = 'https://sportsbook.draftkings.com//sites/US-SB/api/v5/eventgroups/84240';

  const PROPS = [
    { category: 1000, subcategory: 10015, label: 'hits' },
    { category: 1000, subcategory: 10016, label: 'hr' },
    { category: 1000, subcategory: 10019, label: 'strikeouts' },
  ];

  function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    console.log('Downloaded:', filename, '(' + data.length + ' records)');
  }

  async function fetchProps(category, subcategory, label) {
    const url = BASE + '/categories/' + category + '/subcategories/' + subcategory + '?format=json';
    console.log('Fetching', label, '...');
    const res = await fetch(url);
    if (!res.ok) {
      console.error(label + ': HTTP ' + res.status);
      return [];
    }
    const data = await res.json();
    const records = [];
    const eventGroup = data.eventGroup || {};
    const events = eventGroup.events || [];

    for (const cat of (eventGroup.offerCategories || [])) {
      for (const sub of (cat.offerSubcategoryDescriptors || [])) {
        const subcategory = sub.offerSubcategory || {};
        for (const offerList of (subcategory.offers || [])) {
          for (const offer of offerList) {
            const eventId = offer.eventId;
            const ev = events.find(e => e.eventId === eventId);
            const gameName = ev ? ev.name : '';
            for (const outcome of (offer.outcomes || [])) {
              if ((outcome.label || '').toLowerCase() !== 'over') continue;
              const oddsInt = parseInt(outcome.oddsAmerican);
              records.push({
                player:     outcome.participant || outcome.label || '',
                prop_type:  label,
                line:       outcome.line,
                odds:       outcome.oddsAmerican,
                plus_money: !isNaN(oddsInt) && oddsInt > 0,
                game:       gameName,
                pulled_at:  new Date().toISOString(),
              });
            }
          }
        }
      }
    }
    console.log(label + ': ' + records.length + ' props found');
    return records;
  }

  // Fetch all prop types
  const hits        = await fetchProps(1000, 10015, 'hits');
  const hr          = await fetchProps(1000, 10016, 'hr');
  const strikeouts  = await fetchProps(1000, 10019, 'strikeouts');

  const batterProps  = [...hits, ...hr];
  const pitcherProps = strikeouts;

  // Download files
  downloadJSON(batterProps,  'mlb_batter_props.json');
  downloadJSON(pitcherProps, 'mlb_pitcher_props.json');

  console.log('Done! Move the downloaded files into your mlb-betting-agent folder, then run merge_props.py');
})();
