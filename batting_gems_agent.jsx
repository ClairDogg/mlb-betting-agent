import { useState, useMemo } from "react";

// ─── Sample data (replace with batter_splits.json from scraper) ───────────
// Format mirrors exactly what mlb_scraper.py outputs.
const SAMPLE_DATA = [
  {
    player_name: "Yordan Alvarez",
    team_name: "Houston Astros",
    venue: "Yankee Stadium",
    park_hr_factor: 109,
    park_hit_factor: 101,
    is_home: false,
    opp_pitcher_name: "Gerrit Cole",
    opp_pitcher_hand: "R",
    vs_lhp_avg: ".241", vs_lhp_hr: 4,  vs_lhp_h: 28,  vs_lhp_ab: 116,
    vs_rhp_avg: ".312", vs_rhp_hr: 18, vs_rhp_h: 72,  vs_rhp_ab: 231,
    home_avg: ".308", home_hr: 12, home_h: 48,
    away_avg: ".293", away_hr: 10, away_h: 44,
    Apr_avg: ".241", May_avg: ".278", Jun_avg: ".305", Jul_avg: ".322",
    Aug_avg: ".341", Sep_avg: ".315",
    bvp_avg: ".333", bvp_hr: 2, bvp_h: 4, bvp_ab: 12,
    hr_line: 0.5, hr_odds: "+140",
    hit_line: 1.5, hit_odds: "+105",
  },
  {
    player_name: "Freddie Freeman",
    team_name: "Los Angeles Dodgers",
    venue: "Dodger Stadium",
    park_hr_factor: 99,
    park_hit_factor: 100,
    is_home: true,
    opp_pitcher_name: "Corbin Burnes",
    opp_pitcher_hand: "R",
    vs_lhp_avg: ".290", vs_lhp_hr: 3,  vs_lhp_h: 22,  vs_lhp_ab: 76,
    vs_rhp_avg: ".315", vs_rhp_hr: 14, vs_rhp_h: 65,  vs_rhp_ab: 206,
    home_avg: ".330", home_hr: 10, home_h: 56,
    away_avg: ".278", away_hr: 7,  away_h: 33,
    Apr_avg: ".304", May_avg: ".318", Jun_avg: ".292", Jul_avg: ".335",
    Aug_avg: ".348", Sep_avg: ".301",
    bvp_avg: ".400", bvp_hr: 1, bvp_h: 4, bvp_ab: 10,
    hr_line: 0.5, hr_odds: "+150",
    hit_line: 1.5, hit_odds: "-110",
  },
  {
    player_name: "Matt Olson",
    team_name: "Atlanta Braves",
    venue: "Truist Park",
    park_hr_factor: 102,
    park_hit_factor: 100,
    is_home: true,
    opp_pitcher_name: "Spencer Strider",
    opp_pitcher_hand: "R",
    vs_lhp_avg: ".255", vs_lhp_hr: 6,  vs_lhp_h: 20,  vs_lhp_ab: 78,
    vs_rhp_avg: ".245", vs_rhp_hr: 22, vs_rhp_h: 58,  vs_rhp_ab: 237,
    home_avg: ".260", home_hr: 15, home_h: 42,
    away_avg: ".238", away_hr: 13, away_h: 36,
    Apr_avg: ".220", May_avg: ".255", Jun_avg: ".280", Jul_avg: ".295",
    Aug_avg: ".270", Sep_avg: ".248",
    bvp_avg: ".125", bvp_hr: 0, bvp_h: 1, bvp_ab: 8,
    hr_line: 0.5, hr_odds: "+165",
    hit_line: 1.5, hit_odds: "+115",
  },
  {
    player_name: "Gunnar Henderson",
    team_name: "Baltimore Orioles",
    venue: "Camden Yards",
    park_hr_factor: 105,
    park_hit_factor: 103,
    is_home: true,
    opp_pitcher_name: "Kevin Gausman",
    opp_pitcher_hand: "R",
    vs_lhp_avg: ".261", vs_lhp_hr: 5,  vs_lhp_h: 18,  vs_lhp_ab: 69,
    vs_rhp_avg: ".282", vs_rhp_hr: 16, vs_rhp_h: 55,  vs_rhp_ab: 195,
    home_avg: ".299", home_hr: 13, home_h: 47,
    away_avg: ".258", away_hr: 8,  away_h: 26,
    Apr_avg: ".275", May_avg: ".291", Jun_avg: ".305", Jul_avg: ".278",
    Aug_avg: ".320", Sep_avg: ".288",
    bvp_avg: ".000", bvp_hr: 0, bvp_h: 0, bvp_ab: 3,
    hr_line: 0.5, hr_odds: "+180",
    hit_line: 1.5, hit_odds: "+100",
  },
  {
    player_name: "Cody Bellinger",
    team_name: "New York Yankees",
    venue: "Yankee Stadium",
    park_hr_factor: 109,
    park_hit_factor: 101,
    is_home: true,
    opp_pitcher_name: "Framber Valdez",
    opp_pitcher_hand: "L",
    vs_lhp_avg: ".198", vs_lhp_hr: 2,  vs_lhp_h: 14,  vs_lhp_ab: 71,
    vs_rhp_avg: ".275", vs_rhp_hr: 12, vs_rhp_h: 44,  vs_rhp_ab: 160,
    home_avg: ".272", home_hr: 9,  home_h: 35,
    away_avg: ".220", away_hr: 5,  away_h: 23,
    Apr_avg: ".245", May_avg: ".260", Jun_avg: ".215", Jul_avg: ".279",
    Aug_avg: ".261", Sep_avg: ".238",
    bvp_avg: ".182", bvp_hr: 0, bvp_h: 2, bvp_ab: 11,
    hr_line: 0.5, hr_odds: "+200",
    hit_line: 1.5, hit_odds: "+130",
  },
];

// ─── Scoring Engine ───────────────────────────────────────────────────────

const MONTHS = ["Apr","May","Jun","Jul","Aug","Sep","Oct"];

function getCurrentMonth() {
  const m = new Date().getMonth(); // 0-indexed
  return MONTHS[Math.max(0, m - 3)] || "Aug"; // baseball season offset
}

function scoreHandedness(batter) {
  const hand = batter.opp_pitcher_hand;
  const avg = parseFloat(hand === "L" ? batter.vs_lhp_avg : batter.vs_rhp_avg) || 0;
  const ab  = hand === "L" ? batter.vs_lhp_ab : batter.vs_rhp_ab;
  if (ab < 20) return { score: 0, note: `vs ${hand}HP — thin sample (${ab} AB)` };
  if (avg >= 0.300) return { score: 2, note: `vs ${hand}HP .${String(Math.round(avg*1000)).padStart(3,"0")} avg (${ab} AB) ✓` };
  if (avg >= 0.265) return { score: 1, note: `vs ${hand}HP .${String(Math.round(avg*1000)).padStart(3,"0")} avg (${ab} AB)` };
  return { score: 0, note: `vs ${hand}HP .${String(Math.round(avg*1000)).padStart(3,"0")} avg — weak` };
}

function scoreMonthly(batter) {
  const month = getCurrentMonth();
  const avg = parseFloat(batter[`${month}_avg`]) || 0;
  if (!avg) return { score: 0, note: `${month} — no data` };
  if (avg >= 0.310) return { score: 2, note: `${month} avg .${String(Math.round(avg*1000)).padStart(3,"0")} — peak month ✓` };
  if (avg >= 0.270) return { score: 1, note: `${month} avg .${String(Math.round(avg*1000)).padStart(3,"0")}` };
  return { score: 0, note: `${month} avg .${String(Math.round(avg*1000)).padStart(3,"0")} — cold month` };
}

function scoreHomeAway(batter) {
  const avg = parseFloat(batter.is_home ? batter.home_avg : batter.away_avg) || 0;
  const loc = batter.is_home ? "home" : "away";
  if (avg >= 0.300) return { score: 2, note: `${loc} .${String(Math.round(avg*1000)).padStart(3,"0")} avg ✓` };
  if (avg >= 0.265) return { score: 1, note: `${loc} .${String(Math.round(avg*1000)).padStart(3,"0")} avg` };
  return { score: 0, note: `${loc} .${String(Math.round(avg*1000)).padStart(3,"0")} — struggles` };
}

function scorePark(batter, type) {
  const factor = type === "hr" ? batter.park_hr_factor : batter.park_hit_factor;
  if (factor >= 108) return { score: 2, note: `park HR factor ${factor} — hitter friendly ✓` };
  if (factor >= 102) return { score: 1, note: `park HR factor ${factor} — slight boost` };
  if (factor <= 92)  return { score: -1, note: `park HR factor ${factor} — pitcher park ✗` };
  return { score: 0, note: `park HR factor ${factor} — neutral` };
}

function scoreBvP(batter) {
  const ab  = batter.bvp_ab || 0;
  const avg = parseFloat(batter.bvp_avg) || 0;
  if (ab < 5) return { score: 0, note: `vs ${batter.opp_pitcher_name} — ${ab} AB, too thin` };
  if (avg >= 0.350) return { score: 2, note: `vs ${batter.opp_pitcher_name} .${String(Math.round(avg*1000)).padStart(3,"0")} in ${ab} AB ✓` };
  if (avg >= 0.270) return { score: 1, note: `vs ${batter.opp_pitcher_name} .${String(Math.round(avg*1000)).padStart(3,"0")} in ${ab} AB` };
  return { score: -1, note: `vs ${batter.opp_pitcher_name} .${String(Math.round(avg*1000)).padStart(3,"0")} in ${ab} AB ✗` };
}

function isPlusMoney(odds) {
  return typeof odds === "string" && odds.startsWith("+");
}

function scoreBatter(batter) {
  const h = scoreHandedness(batter);
  const m = scoreMonthly(batter);
  const ha = scoreHomeAway(batter);
  const pk = scorePark(batter, "hr");
  const bvp = scoreBvP(batter);
  const total = h.score + m.score + ha.score + pk.score + bvp.score;

  // HR prop evaluation
  const hrPlus = isPlusMoney(batter.hr_odds);
  const hrBet  = total >= 3 ? (hrPlus ? "★ BEST BET" : "BET OVER") : total >= 2 ? "LEAN OVER" : "PASS";

  // Hit prop evaluation (primarily home/away + park hits factor + monthly)
  const hitPk  = scorePark(batter, "hits");
  const hitTotal = m.score + ha.score + hitPk.score + bvp.score;
  const hitPlus  = isPlusMoney(batter.hit_odds);
  const hitBet   = hitTotal >= 3 ? (hitPlus ? "★ BEST BET" : "BET OVER") : hitTotal >= 2 ? "LEAN OVER" : "PASS";

  return {
    ...batter,
    factors: { handedness: h, monthly: m, homeaway: ha, park: pk, bvp },
    gemScore: total,
    hrBet, hrPlus,
    hitBet, hitPlus,
  };
}

// ─── Component ────────────────────────────────────────────────────────────

const STYLE = {
  base: {
    fontFamily: "system-ui, -apple-system, sans-serif",
    fontSize: 15,
    background: "#fff",
    color: "#111",
    padding: "20px 24px",
    maxWidth: 900,
    margin: "0 auto",
    lineHeight: 1.6,
  },
  header: {
    borderBottom: "2px solid #111",
    paddingBottom: 8,
    marginBottom: 20,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-end",
  },
  title: { fontSize: 20, fontWeight: 700, margin: 0 },
  subtitle: { fontSize: 13, color: "#555", margin: "2px 0 0" },
  bestCount: { fontSize: 13, fontWeight: 600 },
  // Filter bar
  filterRow: { display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" },
  filterBtn: (active) => ({
    padding: "4px 12px", fontSize: 13, border: "1px solid #111",
    background: active ? "#111" : "#fff", color: active ? "#fff" : "#111",
    cursor: "pointer", borderRadius: 2,
  }),
  // Batter card
  card: (isBest) => ({
    border: isBest ? "2px solid #111" : "1px solid #ccc",
    marginBottom: 12,
    borderRadius: 2,
    overflow: "hidden",
  }),
  cardHeader: (isBest) => ({
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "7px 12px",
    background: isBest ? "#111" : "#f5f5f5",
    color: isBest ? "#fff" : "#111",
    fontWeight: 600,
    fontSize: 15,
    cursor: "pointer",
  }),
  gemScore: (score) => ({
    fontSize: 12,
    fontWeight: 700,
    padding: "2px 8px",
    border: "1px solid currentColor",
    borderRadius: 10,
  }),
  body: { padding: "10px 12px" },
  // Prop row
  propRow: {
    display: "grid",
    gridTemplateColumns: "130px 60px 60px 70px 110px",
    gap: 4,
    fontSize: 14,
    padding: "3px 0",
    borderBottom: "1px solid #eee",
  },
  propHeader: {
    display: "grid",
    gridTemplateColumns: "130px 60px 60px 70px 110px",
    gap: 4,
    fontSize: 11,
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    paddingBottom: 4,
    borderBottom: "1px solid #ddd",
    marginBottom: 2,
  },
  verdictBest: { fontWeight: 700, color: "#111" },
  verdictLean: { color: "#555" },
  verdictPass: { color: "#aaa" },
  plusOdds: { fontWeight: 600 },
  // Factor breakdown
  factorList: { marginTop: 8, fontSize: 13, color: "#444" },
  factorRow: (score) => ({
    display: "flex", gap: 6, alignItems: "center", padding: "1px 0",
    color: score >= 2 ? "#111" : score === 1 ? "#444" : score < 0 ? "#aaa" : "#888",
  }),
  dot: (score) => ({
    width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
    background: score >= 2 ? "#111" : score === 1 ? "#777" : score < 0 ? "#ddd" : "#bbb",
  }),
};

function verdictStyle(v) {
  if (v.startsWith("★")) return STYLE.verdictBest;
  if (v.startsWith("BET")) return { fontWeight: 600 };
  if (v.startsWith("LEAN")) return STYLE.verdictLean;
  return STYLE.verdictPass;
}

function BatterCard({ batter }) {
  const [open, setOpen] = useState(false);
  const isBest = batter.hrBet.startsWith("★") || batter.hitBet.startsWith("★");
  const loc = batter.is_home ? "Home" : "Away";

  return (
    <div style={STYLE.card(isBest)}>
      <div style={STYLE.cardHeader(isBest)} onClick={() => setOpen(o => !o)}>
        <span>
          {batter.player_name}
          <span style={{ fontWeight: 400, fontSize: 13, marginLeft: 10, opacity: 0.75 }}>
            {batter.team_name} · {loc} vs {batter.opp_pitcher_hand}HP {batter.opp_pitcher_name} · {batter.venue}
          </span>
        </span>
        <span style={STYLE.gemScore(batter.gemScore)}>
          {batter.gemScore >= 3 ? "💎 " : ""}{batter.gemScore}/7
        </span>
      </div>

      <div style={STYLE.body}>
        {/* Prop grid */}
        <div style={STYLE.propHeader}>
          <span>Prop</span>
          <span>Line</span>
          <span>Odds</span>
          <span></span>
          <span>Verdict</span>
        </div>

        {/* HR row */}
        <div style={STYLE.propRow}>
          <span>Home Runs</span>
          <span>{batter.hr_line}</span>
          <span style={batter.hrPlus ? STYLE.plusOdds : {}}>
            {batter.hr_odds}
          </span>
          <span></span>
          <span style={verdictStyle(batter.hrBet)}>{batter.hrBet}</span>
        </div>

        {/* Hits row */}
        <div style={STYLE.propRow}>
          <span>Hits</span>
          <span>{batter.hit_line}</span>
          <span style={batter.hitPlus ? STYLE.plusOdds : {}}>
            {batter.hit_odds}
          </span>
          <span></span>
          <span style={verdictStyle(batter.hitBet)}>{batter.hitBet}</span>
        </div>

        {/* Factor breakdown (toggle) */}
        {open && (
          <div style={STYLE.factorList}>
            <div style={{ fontSize: 11, color: "#aaa", marginTop: 8, marginBottom: 3,
                          textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Factor Breakdown
            </div>
            {Object.entries(batter.factors).map(([key, f]) => (
              <div key={key} style={STYLE.factorRow(f.score)}>
                <div style={STYLE.dot(f.score)} />
                <span>{f.note}</span>
              </div>
            ))}
          </div>
        )}

        <div style={{ fontSize: 11, color: "#bbb", marginTop: 6, cursor: "pointer" }}
             onClick={() => setOpen(o => !o)}>
          {open ? "▲ hide factors" : "▼ show factors"}
        </div>
      </div>
    </div>
  );
}

export default function HiddenGemsAgent() {
  const [filter, setFilter] = useState("all");

  const scored = useMemo(() =>
    SAMPLE_DATA.map(scoreBatter).sort((a, b) => b.gemScore - a.gemScore),
    []
  );

  const filtered = useMemo(() => {
    if (filter === "best")  return scored.filter(b => b.hrBet.startsWith("★") || b.hitBet.startsWith("★"));
    if (filter === "hr")    return scored.filter(b => b.hrBet !== "PASS");
    if (filter === "hits")  return scored.filter(b => b.hitBet !== "PASS");
    if (filter === "plus")  return scored.filter(b => b.hrPlus || b.hitPlus);
    return scored;
  }, [scored, filter]);

  const bestCount = scored.filter(b => b.hrBet.startsWith("★") || b.hitBet.startsWith("★")).length;

  return (
    <div style={STYLE.base}>
      <div style={STYLE.header}>
        <div>
          <div style={STYLE.title}>Hidden Gems · Batting Props</div>
          <div style={STYLE.subtitle}>
            HR · Hits · Scored across: handedness, monthly trend, home/away, park factor, head-to-head
          </div>
        </div>
        <div style={STYLE.bestCount}>★ Best Bets: {bestCount}</div>
      </div>

      {/* Filters */}
      <div style={STYLE.filterRow}>
        {[
          ["all",  "All Players"],
          ["best", "★ Best Bets"],
          ["plus", "+ Odds Only"],
          ["hr",   "HR Props"],
          ["hits", "Hit Props"],
        ].map(([key, label]) => (
          <button key={key} style={STYLE.filterBtn(filter === key)}
                  onClick={() => setFilter(key)}>{label}</button>
        ))}
      </div>

      {filtered.length === 0 && (
        <div style={{ color: "#888", fontSize: 14 }}>No players match this filter today.</div>
      )}

      {filtered.map(b => <BatterCard key={b.player_name} batter={b} />)}

      <div style={{ fontSize: 11, color: "#bbb", marginTop: 20, borderTop: "1px solid #eee", paddingTop: 8 }}>
        Sample data shown — replace SAMPLE_DATA with output from mlb_scraper.py · Gem score = sum of 5 factors (handedness, monthly, home/away, park, bvp) · score ≥3 = BET, plus money = ★ BEST BET
      </div>
    </div>
  );
}
