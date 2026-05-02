import { useState, useMemo, useEffect } from "react";

// ─── Scoring Engine ───────────────────────────────────────────────────────

function scoreHandedness(batter) {
  const hand = batter.pitcher_throws;
  const avg = parseFloat(batter.handedness_avg) || 0;
  const ops = parseFloat(batter.handedness_ops) || 0;
  if (!hand) return { score: 0, note: "vs pitcher — no handedness data" };
  if (avg === 0 && ops === 0) return { score: 0, note: `vs ${hand}HP — no split data` };
  if (avg >= 0.300) return { score: 2, note: `vs ${hand}HP .${String(Math.round(avg*1000)).padStart(3,"0")} avg ✓` };
  if (avg >= 0.265) return { score: 1, note: `vs ${hand}HP .${String(Math.round(avg*1000)).padStart(3,"0")} avg` };
  return { score: 0, note: `vs ${hand}HP .${String(Math.round(avg*1000)).padStart(3,"0")} avg — weak` };
}

function scoreMonthly(batter) {
  const avg = parseFloat(batter.monthly_avg) || 0;
  const month = new Date().toLocaleString("default", { month: "short" });
  if (!avg) return { score: 0, note: `${month} — no data` };
  if (avg >= 0.310) return { score: 2, note: `${month} avg .${String(Math.round(avg*1000)).padStart(3,"0")} — hot ✓` };
  if (avg >= 0.270) return { score: 1, note: `${month} avg .${String(Math.round(avg*1000)).padStart(3,"0")}` };
  return { score: 0, note: `${month} avg .${String(Math.round(avg*1000)).padStart(3,"0")} — cold` };
}

function scoreHomeAway(batter) {
  const avg = parseFloat(batter.home_away_avg) || 0;
  const loc = batter.home_away || "home";
  if (!avg) return { score: 0, note: `${loc} — no data` };
  if (avg >= 0.300) return { score: 2, note: `${loc} .${String(Math.round(avg*1000)).padStart(3,"0")} avg ✓` };
  if (avg >= 0.265) return { score: 1, note: `${loc} .${String(Math.round(avg*1000)).padStart(3,"0")} avg` };
  return { score: 0, note: `${loc} .${String(Math.round(avg*1000)).padStart(3,"0")} — struggles` };
}

function scorePark(batter) {
  const factor = parseFloat(batter.park_factor) || 100;
  if (factor >= 108) return { score: 2, note: `park factor ${factor} — hitter friendly ✓` };
  if (factor >= 102) return { score: 1, note: `park factor ${factor} — slight boost` };
  if (factor <= 92)  return { score: -1, note: `park factor ${factor} — pitcher park ✗` };
  return { score: 0, note: `park factor ${factor} — neutral` };
}

function scoreBvP(batter) {
  const ab  = parseFloat(batter.bvp_abs) || 0;
  const avg = parseFloat(batter.bvp_avg) || 0;
  const pitcher = batter.pitcher_throws ? `vs ${batter.pitcher_throws}HP pitcher` : "vs pitcher";
  if (ab < 5) return { score: 0, note: `${pitcher} — ${ab} AB, too thin` };
  if (avg >= 0.350) return { score: 2, note: `${pitcher} .${String(Math.round(avg*1000)).padStart(3,"0")} in ${ab} AB ✓` };
  if (avg >= 0.270) return { score: 1, note: `${pitcher} .${String(Math.round(avg*1000)).padStart(3,"0")} in ${ab} AB` };
  return { score: -1, note: `${pitcher} .${String(Math.round(avg*1000)).padStart(3,"0")} in ${ab} AB ✗` };
}

function isPlusMoney(odds) {
  if (odds === null || odds === undefined) return false;
  return String(odds).startsWith("+") || Number(odds) > 0;
}

function formatOdds(odds) {
  if (odds === null || odds === undefined) return "—";
  const n = Number(odds);
  if (isNaN(n)) return String(odds);
  return n > 0 ? `+${n}` : String(n);
}

function scoreBatter(batter) {
  const h   = scoreHandedness(batter);
  const m   = scoreMonthly(batter);
  const ha  = scoreHomeAway(batter);
  const pk  = scorePark(batter);
  const bvp = scoreBvP(batter);
  const total = h.score + m.score + ha.score + pk.score + bvp.score;

  const hasProps = batter.prop_type !== null && batter.prop_type !== undefined;
  const odds = batter.odds;
  const plus = isPlusMoney(odds);

  let verdict = "PASS";
  if (hasProps) {
    if (total >= 3 && plus) verdict = "★ BEST BET";
    else if (total >= 3)    verdict = "BET OVER";
    else if (total >= 2)    verdict = "LEAN OVER";
  } else {
    if (total >= 3)         verdict = "BET OVER (no line yet)";
    else if (total >= 2)    verdict = "LEAN OVER";
  }

  return {
    ...batter,
    factors: { handedness: h, monthly: m, homeaway: ha, park: pk, bvp },
    gemScore: total,
    verdict,
    plus,
    hasProps,
  };
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const STYLE = {
  base: {
    fontFamily: "system-ui, -apple-system, sans-serif",
    fontSize: 15,
    background: "#fff",
    color: "#111",
    padding: "20px 24px",
    maxWidth: 960,
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
  filterRow: { display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" },
  filterBtn: (active) => ({
    padding: "4px 12px", fontSize: 13, border: "1px solid #111",
    background: active ? "#111" : "#fff", color: active ? "#fff" : "#111",
    cursor: "pointer", borderRadius: 2,
  }),
  card: (isBest) => ({
    border: isBest ? "2px solid #111" : "1px solid #ccc",
    marginBottom: 10,
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
  gemScore: {
    fontSize: 12, fontWeight: 700,
    padding: "2px 8px", border: "1px solid currentColor", borderRadius: 10,
  },
  body: { padding: "10px 12px" },
  propGrid: {
    display: "grid",
    gridTemplateColumns: "100px 55px 70px 140px",
    gap: 6,
    fontSize: 14,
    padding: "3px 0",
    borderBottom: "1px solid #eee",
    alignItems: "center",
  },
  propHeader: {
    display: "grid",
    gridTemplateColumns: "100px 55px 70px 140px",
    gap: 6,
    fontSize: 11,
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    paddingBottom: 4,
    borderBottom: "1px solid #ddd",
    marginBottom: 2,
  },
  verdictBest: { fontWeight: 700 },
  verdictLean: { color: "#555" },
  verdictPass: { color: "#aaa" },
  plusOdds: { fontWeight: 600, color: "#111" },
  factorList: { marginTop: 8, fontSize: 13, color: "#444" },
  factorRow: (score) => ({
    display: "flex", gap: 6, alignItems: "center", padding: "1px 0",
    color: score >= 2 ? "#111" : score === 1 ? "#444" : score < 0 ? "#bbb" : "#888",
  }),
  dot: (score) => ({
    width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
    background: score >= 2 ? "#111" : score === 1 ? "#777" : score < 0 ? "#ddd" : "#bbb",
  }),
};

function verdictStyle(v) {
  if (!v) return STYLE.verdictPass;
  if (v.startsWith("★")) return STYLE.verdictBest;
  if (v.startsWith("BET")) return { fontWeight: 600 };
  if (v.startsWith("LEAN")) return STYLE.verdictLean;
  return STYLE.verdictPass;
}

// ─── Batter Card ──────────────────────────────────────────────────────────────

function BatterCard({ batter }) {
  const [open, setOpen] = useState(false);
  const isBest = batter.verdict.startsWith("★");

  return (
    <div style={STYLE.card(isBest)}>
      <div style={STYLE.cardHeader(isBest)} onClick={() => setOpen(o => !o)}>
        <span>
          {batter.player}
          <span style={{ fontWeight: 400, fontSize: 13, marginLeft: 10, opacity: 0.75 }}>
            {batter.team} · {batter.home_away || ""} · {batter.venue || ""} · {batter.game || ""}
          </span>
        </span>
        <span style={STYLE.gemScore}>
          {batter.gemScore >= 3 ? "💎 " : ""}{batter.gemScore}/7
        </span>
      </div>

      <div style={STYLE.body}>
        <div style={STYLE.propHeader}>
          <span>Prop</span>
          <span>Line</span>
          <span>Odds</span>
          <span>Verdict</span>
        </div>
        <div style={STYLE.propGrid}>
          <span>{batter.prop_type || "—"}</span>
          <span>{batter.line ?? "—"}</span>
          <span style={batter.plus ? STYLE.plusOdds : {}}>
            {formatOdds(batter.odds)}
          </span>
          <span style={verdictStyle(batter.verdict)}>{batter.verdict}</span>
        </div>

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

// ─── Main Component ───────────────────────────────────────────────────────────

export default function HiddenGemsAgent() {
  const [filter, setFilter] = useState("all");
  const [rawData, setRawData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("./merged_batter_data.json")
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => { setRawData(data); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  const scored = useMemo(() =>
    rawData.map(scoreBatter).sort((a, b) => b.gemScore - a.gemScore),
    [rawData]
  );

  const filtered = useMemo(() => {
    if (filter === "best")  return scored.filter(b => b.verdict.startsWith("★"));
    if (filter === "bet")   return scored.filter(b => b.verdict.startsWith("BET") || b.verdict.startsWith("★"));
    if (filter === "lean")  return scored.filter(b => b.gemScore >= 2);
    if (filter === "plus")  return scored.filter(b => b.plus);
    if (filter === "props") return scored.filter(b => b.hasProps);
    return scored;
  }, [scored, filter]);

  const bestCount = scored.filter(b => b.verdict.startsWith("★")).length;
  const betCount  = scored.filter(b => b.verdict.startsWith("BET") || b.verdict.startsWith("★")).length;

  if (loading) return (
    <div style={{ ...STYLE.base, color: "#888", paddingTop: 60, textAlign: "center" }}>
      Loading today's data...
    </div>
  );

  if (error) return (
    <div style={{ ...STYLE.base, paddingTop: 40 }}>
      <div style={{ color: "#c00", fontWeight: 600, marginBottom: 8 }}>
        Could not load merged_batter_data.json
      </div>
      <div style={{ fontSize: 13, color: "#555" }}>
        Error: {error}<br /><br />
        Make sure you've run:<br />
        <code>python3 mlb_stats_scraper.py</code><br />
        <code>python3 merge_props.py</code><br />
        and that <strong>merged_batter_data.json</strong> is in the same folder as this file.
      </div>
    </div>
  );

  return (
    <div style={STYLE.base}>
      <div style={STYLE.header}>
        <div>
          <div style={STYLE.title}>⚾ Hidden Gems · Batting Props</div>
          <div style={STYLE.subtitle}>
            Scored across: handedness, monthly trend, home/away, park factor, head-to-head · {scored.length} batters today
          </div>
        </div>
        <div style={STYLE.bestCount}>
          ★ {bestCount} best bets · BET {betCount} total
        </div>
      </div>

      <div style={STYLE.filterRow}>
        {[
          ["all",   `All (${scored.length})`],
          ["best",  `★ Best Bets (${bestCount})`],
          ["bet",   `BET OVER (${betCount})`],
          ["lean",  "Lean Over"],
          ["plus",  "+ Odds Only"],
          ["props", "Has Props"],
        ].map(([key, label]) => (
          <button key={key} style={STYLE.filterBtn(filter === key)}
                  onClick={() => setFilter(key)}>{label}</button>
        ))}
      </div>

      {filtered.length === 0 && (
        <div style={{ color: "#888", fontSize: 14 }}>No players match this filter today.</div>
      )}

      {filtered.map((b, i) => <BatterCard key={`${b.player}-${i}`} batter={b} />)}

      <div style={{ fontSize: 11, color: "#bbb", marginTop: 20, borderTop: "1px solid #eee", paddingTop: 8 }}>
        Data from MLB Stats API + DraftKings · Gem score /7 (handedness, monthly, home/away, park, BvP) ·
        Score ≥3 = BET OVER · Score ≥3 + plus money = ★ BEST BET
      </div>
    </div>
  );
}
