import { useState, useMemo, useEffect } from "react";

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
          <span>{batter.hr_line ?? "—"}</span>
          <span style={batter.hrPlus ? STYLE.plusOdds : {}}>
            {batter.hr_odds ?? "N/A"}
          </span>
          <span></span>
          <span style={verdictStyle(batter.hrBet)}>{batter.hrBet}</span>
        </div>

        {/* Hits row */}
        <div style={STYLE.propRow}>
          <span>Hits</span>
          <span>{batter.hit_line ?? "—"}</span>
          <span style={batter.hitPlus ? STYLE.plusOdds : {}}>
            {batter.hit_odds ?? "N/A"}
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
  const [rawData, setRawData] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    fetch("./merged_batter_data.json")
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
      .catch(() => fetch("./batter_splits.json").then(r => r.json()))
      .then(setRawData)
      .catch(e => setLoadError(e.message));
  }, []);

  const scored = useMemo(() => {
    if (!rawData) return [];
    return rawData.map(scoreBatter).sort((a, b) => b.gemScore - a.gemScore);
  }, [rawData]);

  const filtered = useMemo(() => {
    if (filter === "best")  return scored.filter(b => b.hrBet.startsWith("★") || b.hitBet.startsWith("★"));
    if (filter === "hr")    return scored.filter(b => b.hrBet !== "PASS");
    if (filter === "hits")  return scored.filter(b => b.hitBet !== "PASS");
    if (filter === "plus")  return scored.filter(b => b.hrPlus || b.hitPlus);
    return scored;
  }, [scored, filter]);

  const bestCount = scored.filter(b => b.hrBet.startsWith("★") || b.hitBet.startsWith("★")).length;

  if (loadError) return (
    <div style={{ ...STYLE.base, color: "#c00" }}>
      Failed to load data: {loadError}<br />
      Make sure you ran <code>python3 mlb_stats_scraper.py</code> and are serving via <code>python3 -m http.server 8080</code>.
    </div>
  );

  if (!rawData) return (
    <div style={{ ...STYLE.base, color: "#888" }}>Loading today's data…</div>
  );

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
        Data: merged_batter_data.json (falls back to batter_splits.json) · Gem score = sum of 5 factors (handedness, monthly, home/away, park, bvp) · score ≥3 = BET, plus money = ★ BEST BET
      </div>
    </div>
  );
}
