import { useState, useEffect, useCallback, useRef } from "react";

// ─── API Configuration ──────────────────────────────────────────────────────
const getApiBase = () => {
  // In Docker/production, use environment variable
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // In development, construct the URL dynamically
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = 8000; // Backend port
  
  // If the app is served through a public domain, prefer same-origin /api.
  if (hostname !== "localhost" && hostname !== "127.0.0.1") {
    return `${window.location.origin}/api/v1`;
  }

  return `${protocol}//${hostname}:${port}/api/v1`;
};

const API_BASE = getApiBase();

// ─── API Client with Error Handling ─────────────────────────────────────────
async function api(path, options = {}) {
  const url = `${API_BASE}${path}`;
  
  try {
    const res = await fetch(url, {
      headers: { 
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });
    
    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`API ${res.status}: ${errorText || res.statusText}`);
    }
    
    return await res.json();
  } catch (error) {
    console.error(`API Error on ${path}:`, error);
    throw error;
  }
}

// ─── Icons ──────────────────────────────────────────────────────────────────
const IconFilter = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
  </svg>
);
const IconSearch = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
  </svg>
);
const IconChevron = ({ dir = "down" }) => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
    style={{ transform: dir === "up" ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>
    <polyline points="6 9 12 15 18 9"/>
  </svg>
);
const IconX = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconRefresh = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
);
const IconBrain = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2a5 5 0 0 1 5 5c0 1.5-.7 2.8-1.7 3.7A6 6 0 0 1 18 16a6 6 0 0 1-6 6 6 6 0 0 1-6-6 6 6 0 0 1 2.7-5.3A5 5 0 0 1 7 7a5 5 0 0 1 5-5z"/>
    <circle cx="10" cy="13" r="1" fill="currentColor"/><circle cx="14" cy="13" r="1" fill="currentColor"/>
    <path d="M10 17c.5.3 1.2.5 2 .5s1.5-.2 2-.5"/>
  </svg>
);
const IconArrowUp = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
  </svg>
);
const IconArrowDown = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>
  </svg>
);
const IconSave = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
  </svg>
);
const IconChevronLeft = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6"/>
  </svg>
);
const IconChevronRight = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6"/>
  </svg>
);

// ─── Utilities ──────────────────────────────────────────────────────────────
const fmt = (v, suffix = "", prefix = "") => v == null ? "N/A" : `${prefix}${v}${suffix}`;
const fmtPct = (v) => v == null ? "N/A" : `${v > 0 ? "+" : ""}${v}%`;
const fmtCap = (v) => v == null ? "N/A" : v >= 1000 ? `${(v/1000).toFixed(1)}T $` : `${v.toFixed(1)}Md $`;
const fmtPrice = (v) => (v == null || v <= 0 ? "N/A" : v.toFixed(2));
const colorForValue = (v, inv) => {
  if (v == null) return "var(--ms-text-muted)";
  const p = inv ? v < 0 : v > 0, n = inv ? v > 0 : v < 0;
  return p ? "var(--ms-green)" : n ? "var(--ms-red)" : "var(--ms-text-muted)";
};
const signalColor = (s) => !s ? "var(--ms-text-muted)" : s.includes("ACHAT FORT") ? "var(--ms-green)" : s.includes("ACHAT") ? "var(--ms-green-soft)" : s.includes("NEUTRE") ? "var(--ms-amber)" : s.includes("VENTE FORTE") ? "var(--ms-red)" : s.includes("VENTE") ? "var(--ms-red-soft)" : "var(--ms-text-muted)";
const scoreColor = (v) => v >= 75 ? "var(--ms-green)" : v >= 55 ? "var(--ms-green-soft)" : v >= 45 ? "var(--ms-amber)" : v >= 30 ? "var(--ms-red-soft)" : "var(--ms-red)";
const getNestedValue = (obj, path) => path.split('.').reduce((o, k) => o && o[k], obj);

// ─── Column Definitions ─────────────────────────────────────────────────────
const COLUMNS = {
  performance: [
    { key: "change1d", label: "1 Jour", fmt: fmtPct, color: true, width: 80, sortKey: "change_1d" },
    { key: "change1w", label: "1 Sem.", fmt: fmtPct, color: true, width: 80, sortKey: "change_1w" },
    { key: "change1m", label: "1 Mois", fmt: fmtPct, color: true, width: 80, sortKey: "change_1m" },
    { key: "changeYTD", label: "YTD", fmt: fmtPct, color: true, width: 80, sortKey: "change_ytd" },
  ],
  fondamentaux: [
    { key: "per", label: "PER", fmt: v => fmt(v, "x"), width: 70, sortKey: "per" },
    { key: "peg", label: "PEG", fmt: v => fmt(v), width: 65, sortKey: "peg" },
    { key: "pbr", label: "P/B", fmt: v => fmt(v, "x"), width: 65, sortKey: "pbr" },
    { key: "evEbitda", label: "EV/EBITDA", fmt: v => fmt(v, "x"), width: 85, sortKey: "ev_ebitda" },
    { key: "dividendYield", label: "Div. %", fmt: v => fmt(v, "%"), width: 70, sortKey: "dividend_yield" },
    { key: "roe", label: "ROE", fmt: v => fmt(v, "%"), color: true, width: 70, sortKey: "roe" },
    { key: "marginEbit", label: "Marge EBIT", fmt: v => fmt(v, "%"), width: 90, sortKey: "margin_ebit" },
  ],
  croissance: [
    { key: "revenueGrowth", label: "Crois. CA", fmt: fmtPct, color: true, width: 90, sortKey: "revenue_growth" },
    { key: "epsGrowth", label: "Crois. BPA", fmt: fmtPct, color: true, width: 90, sortKey: "eps_growth" },
    { key: "fcfYield", label: "FCF Yield", fmt: v => fmt(v, "%"), width: 85, sortKey: "fcf_yield" },
    { key: "netDebtEbitda", label: "DN/EBITDA", fmt: v => fmt(v, "x"), width: 90, sortKey: "net_debt_ebitda", invertColor: true },
    { key: "currentRatio", label: "Ratio Cour.", fmt: v => fmt(v), width: 90, sortKey: "current_ratio" },
  ],
  technique: [
    { key: "rsi", label: "RSI 14", fmt: v => fmt(v), width: 70, sortKey: "rsi" },
    { key: "distMM50", label: "Dist. MM50", fmt: fmtPct, color: true, width: 90, sortKey: "dist_mm50" },
    { key: "distMM200", label: "Dist. MM200", fmt: fmtPct, color: true, width: 95, sortKey: "dist_mm200" },
    { key: "beta", label: "Beta", fmt: v => fmt(v), width: 65, sortKey: "beta" },
    { key: "volatility", label: "Volatilité", fmt: v => fmt(v, "%"), width: 80, sortKey: "volatility" },
    { key: "volume", label: "Vol. (M)", fmt: v => fmt(v, "M"), width: 80, sortKey: "volume_avg" },
  ],
  analystes: [
    { key: "analystRating", label: "Note Anal.", fmt: v => fmt(v, "/5"), width: 85, sortKey: "analyst_rating" },
    { key: "targetPrice", label: "Objectif", fmt: v => fmt(v, " $"), width: 85, sortKey: "target_price" },
    { key: "upside", label: "Potentiel", fmt: fmtPct, color: true, width: 85, sortKey: "upside" },
    { key: "esgScore", label: "ESG", fmt: v => fmt(v, "/100"), width: 75, sortKey: "esg_score" },
  ],
  ia: [
    { key: "aiSignal", label: "Signal IA", fmt: v => v, width: 110, isSignal: true, sortKey: "ai_score_overall" },
    { key: "aiScores.overall", label: "Score IA", fmt: v => fmt(v, "/100"), width: 85, isScore: true, sortKey: "ai_score_overall" },
    { key: "aiScores.fundamental", label: "Fondamental", fmt: v => fmt(v), width: 90, isScore: true, sortKey: "ai_score_fundamental" },
    { key: "aiScores.technical", label: "Technique", fmt: v => fmt(v), width: 80, isScore: true, sortKey: "ai_score_technical" },
    { key: "aiScores.momentum", label: "Momentum", fmt: v => fmt(v), width: 85, isScore: true, sortKey: "ai_score_momentum" },
    { key: "aiScores.risk", label: "Risque", fmt: v => fmt(v), width: 70, isScore: true, sortKey: "ai_score_risk" },
  ],
};
const VIEW_PRESETS = [
  { id: "performance", label: "Performance", cols: "performance" },
  { id: "fondamentaux", label: "Fondamentaux", cols: "fondamentaux" },
  { id: "croissance", label: "Croissance", cols: "croissance" },
  { id: "technique", label: "Technique", cols: "technique" },
  { id: "analystes", label: "Analystes & ESG", cols: "analystes" },
  { id: "ia", label: "Analyse IA", cols: "ia" },
];

// ─── Sub-Components ─────────────────────────────────────────────────────────

function ScoreBar({ value, max = 100, color }) {
  if (value == null) {
    return <span style={{ fontSize: 11, color: "var(--ms-text-muted)", fontWeight: 600 }}>N/A</span>;
  }
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ width: 48, height: 5, borderRadius: 3, background: "var(--ms-bg-tertiary)", overflow: "hidden" }}>
        <div style={{ width: `${(value / max) * 100}%`, height: "100%", borderRadius: 3, background: color || scoreColor(value), transition: "width 0.4s ease" }}/>
      </div>
      <span style={{ fontSize: 11, color: color || scoreColor(value), fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{value}</span>
    </div>
  );
}

function SignalBadge({ signal }) {
  const bg = signalColor(signal);
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 4, fontSize: 10,
      fontWeight: 700, letterSpacing: "0.05em", color: bg, background: `${bg}18`, border: `1px solid ${bg}30`,
      textTransform: "uppercase", whiteSpace: "nowrap",
    }}>
      {signal && signal.includes("ACHAT") && <IconArrowUp />}
      {signal && signal.includes("VENTE") && <IconArrowDown />}
      {signal || "—"}
    </span>
  );
}

function RangeFilter({ def, value, onChange }) {
  const [local, setLocal] = useState(value || [def.min, def.max]);
  useEffect(() => { setLocal(value || [def.min, def.max]); }, [value, def.min, def.max]);
  const commit = (v) => { setLocal(v); onChange(v[0] === def.min && v[1] === def.max ? null : v); };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--ms-text-muted)" }}>
        <span>{local[0]}</span><span>{local[1]}</span>
      </div>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <input type="range" min={def.min} max={def.max} step={def.step} value={local[0]}
          onChange={e => commit([+e.target.value, Math.max(+e.target.value, local[1])])}
          style={{ flex: 1, accentColor: "var(--ms-accent)" }} />
        <input type="range" min={def.min} max={def.max} step={def.step} value={local[1]}
          onChange={e => commit([Math.min(local[0], +e.target.value), +e.target.value])}
          style={{ flex: 1, accentColor: "var(--ms-accent)" }} />
      </div>
    </div>
  );
}

function Pagination({ page, totalPages, total, onPageChange }) {
  if (totalPages <= 1) return null;
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "12px 0" }}>
      <button onClick={() => onPageChange(page - 1)} disabled={page <= 1} style={{
        background: "var(--ms-bg-tertiary)", border: "1px solid var(--ms-border)", borderRadius: 6, padding: "6px 10px",
        cursor: page > 1 ? "pointer" : "not-allowed", color: page > 1 ? "var(--ms-text)" : "var(--ms-text-muted)", display: "flex", alignItems: "center",
        opacity: page <= 1 ? 0.4 : 1,
      }}><IconChevronLeft /></button>
      <span style={{ fontSize: 12, color: "var(--ms-text-secondary)", fontVariantNumeric: "tabular-nums" }}>
        Page {page} / {totalPages} ({total} résultats)
      </span>
      <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages} style={{
        background: "var(--ms-bg-tertiary)", border: "1px solid var(--ms-border)", borderRadius: 6, padding: "6px 10px",
        cursor: page < totalPages ? "pointer" : "not-allowed", color: page < totalPages ? "var(--ms-text)" : "var(--ms-text-muted)", display: "flex", alignItems: "center",
        opacity: page >= totalPages ? 0.4 : 1,
      }}><IconChevronRight /></button>
    </div>
  );
}

function FilterPanel({ filters, setFilters, filterOptions, onClose }) {
  const activeCount = Object.values(filters).filter(v => v != null).length;
  const ranges = filterOptions?.ranges || {};
  const FILTER_DEFS = [
    { key: "country", label: "Pays", type: "select", options: filterOptions?.countries || [] },
    { key: "sector", label: "Secteur", type: "select", options: filterOptions?.sectors || [] },
    { key: "market_index", label: "Indice", type: "select", options: filterOptions?.indices || [] },
    { key: "ai_signal", label: "Signal IA", type: "select", options: filterOptions?.ai_signals || [] },
    { key: "market_cap", label: "Capitalisation (Md $)", type: "range", min: Math.floor(ranges.market_cap?.min || 0), max: Math.ceil(ranges.market_cap?.max || 3000), step: 10 },
    { key: "per", label: "PER", type: "range", min: Math.floor(ranges.per?.min || 0), max: Math.ceil(ranges.per?.max || 80), step: 1 },
    { key: "dividend_yield", label: "Rendement Div. (%)", type: "range", min: 0, max: Math.ceil(ranges.dividend_yield?.max || 10), step: 0.1 },
    { key: "roe", label: "ROE (%)", type: "range", min: Math.floor(ranges.roe?.min || -10), max: Math.ceil(ranges.roe?.max || 50), step: 1 },
    { key: "margin_ebit", label: "Marge EBIT (%)", type: "range", min: Math.floor(ranges.margin_ebit?.min || -5), max: Math.ceil(ranges.margin_ebit?.max || 40), step: 1 },
    { key: "revenue_growth", label: "Croissance CA (%)", type: "range", min: Math.floor(ranges.revenue_growth?.min || -20), max: Math.ceil(ranges.revenue_growth?.max || 60), step: 1 },
    { key: "rsi", label: "RSI", type: "range", min: 0, max: 100, step: 1 },
    { key: "beta", label: "Beta", type: "range", min: 0, max: Math.ceil((ranges.beta?.max || 2.5) * 10) / 10, step: 0.1 },
    { key: "esg_score", label: "Score ESG", type: "range", min: 0, max: 100, step: 1 },
    { key: "ai_score_overall", label: "Score IA", type: "range", min: 0, max: 100, step: 1 },
  ];

  return (
    <div style={{ background: "var(--ms-bg-secondary)", border: "1px solid var(--ms-border)", borderRadius: 10, padding: 16, marginBottom: 12, animation: "slideDown 0.25s ease" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <IconFilter />
          <span style={{ fontWeight: 700, fontSize: 14, color: "var(--ms-text)" }}>Filtres avancés</span>
          {activeCount > 0 && <span style={{ background: "var(--ms-accent)", color: "#fff", borderRadius: 10, fontSize: 10, fontWeight: 700, padding: "1px 7px" }}>{activeCount}</span>}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {activeCount > 0 && (
            <button onClick={() => setFilters({})} style={{ background: "none", border: "1px solid var(--ms-border)", borderRadius: 6, padding: "4px 10px", fontSize: 11, color: "var(--ms-text-muted)", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
              <IconRefresh /> Réinitialiser
            </button>
          )}
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ms-text-muted)", padding: 4 }}><IconX /></button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
        {FILTER_DEFS.map(def => (
          <div key={def.key} style={{
            background: "var(--ms-bg)", borderRadius: 8, padding: "10px 12px",
            border: filters[def.key] != null ? "1px solid var(--ms-accent)" : "1px solid var(--ms-border)", transition: "border-color 0.2s",
          }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: "var(--ms-text-secondary)", marginBottom: 6, display: "block" }}>{def.label}</label>
            {def.type === "select" ? (
              <select value={filters[def.key] || ""} onChange={e => setFilters(f => ({ ...f, [def.key]: e.target.value || null }))}
                style={{ width: "100%", background: "var(--ms-bg-tertiary)", border: "1px solid var(--ms-border)", borderRadius: 5, padding: "5px 8px", fontSize: 12, color: "var(--ms-text)", outline: "none" }}>
                <option value="">Tous</option>
                {def.options.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            ) : (
              <RangeFilter def={def} value={filters[def.key]} onChange={v => setFilters(f => ({ ...f, [def.key]: v }))} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function PresetBar({ onApply }) {
  const [presets, setPresets] = useState([]);
  useEffect(() => { api("/presets").then(d => setPresets(d.presets || [])).catch(() => {}); }, []);
  if (!presets.length) return null;
  return (
    <div style={{ display: "flex", gap: 6, overflowX: "auto", padding: "8px 0", marginBottom: 4 }}>
      {presets.map(p => (
        <button key={p.id} onClick={() => onApply(p)} style={{
          background: "var(--ms-bg-secondary)", border: "1px solid var(--ms-border)", borderRadius: 8, padding: "6px 12px",
          fontSize: 11, fontWeight: 600, color: "var(--ms-text-secondary)", cursor: "pointer", whiteSpace: "nowrap",
          display: "flex", alignItems: "center", gap: 5, transition: "all 0.2s",
        }}
          onMouseOver={e => { e.currentTarget.style.borderColor = "var(--ms-accent)"; e.currentTarget.style.color = "var(--ms-accent)"; }}
          onMouseOut={e => { e.currentTarget.style.borderColor = "var(--ms-border)"; e.currentTarget.style.color = "var(--ms-text-secondary)"; }}
        >
          <span>{p.icon}</span> {p.name}
        </button>
      ))}
    </div>
  );
}

function AIInsightPanel({ ticker, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true); setError(null);
    api(`/ai/analyze/${encodeURIComponent(ticker)}`)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [ticker]);

  return (
    <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, animation: "fadeIn 0.2s ease" }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ background: "var(--ms-bg)", border: "1px solid var(--ms-border)", borderRadius: 14, width: "min(700px, 95vw)", maxHeight: "90vh", overflow: "auto", boxShadow: "0 25px 80px rgba(0,0,0,0.4)", animation: "scaleIn 0.25s ease" }}>
        <div style={{ padding: "20px 24px 16px", borderBottom: "1px solid var(--ms-border)", background: "linear-gradient(135deg, var(--ms-bg-secondary), var(--ms-bg))", borderRadius: "14px 14px 0 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                <span style={{ color: "var(--ms-accent)", display: "flex" }}><IconBrain /></span>
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", color: "var(--ms-accent)", textTransform: "uppercase" }}>Analyse IA</span>
              </div>
              <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--ms-text)" }}>{data?.name || ticker}</h2>
              <span style={{ fontSize: 13, color: "var(--ms-text-muted)" }}>{ticker}</span>
            </div>
            <button onClick={onClose} style={{ background: "var(--ms-bg-tertiary)", border: "none", borderRadius: 8, padding: 8, cursor: "pointer", color: "var(--ms-text-muted)" }}><IconX /></button>
          </div>
          {data && (
            <div style={{ display: "flex", gap: 16, marginTop: 14, alignItems: "center" }}>
              <SignalBadge signal={data.signal} />
            </div>
          )}
        </div>
        <div style={{ padding: "20px 24px" }}>
          {loading && (
            <div style={{ textAlign: "center", padding: "40px 0" }}>
              <div style={{ width: 40, height: 40, margin: "0 auto 16px", border: "3px solid var(--ms-border)", borderTopColor: "var(--ms-accent)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }}/>
              <p style={{ color: "var(--ms-text-muted)", fontSize: 13 }}>Analyse en cours...</p>
            </div>
          )}
          {error && <div style={{ color: "var(--ms-red)", textAlign: "center", padding: 20 }}>Erreur: {error}</div>}
          {data && !loading && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 20 }}>
                {[
                  { label: "Global", val: data.scores.overall },
                  { label: "Fondamental", val: data.scores.fundamental },
                  { label: "Technique", val: data.scores.technical },
                  { label: "Momentum", val: data.scores.momentum },
                  { label: "Risque", val: data.scores.risk },
                ].map(g => (
                  <div key={g.label} style={{ textAlign: "center", background: "var(--ms-bg-secondary)", borderRadius: 10, padding: "14px 8px", border: g.label === "Global" ? `1px solid ${scoreColor(g.val)}40` : "1px solid var(--ms-border)" }}>
                    <div style={{ fontSize: 26, fontWeight: 800, color: scoreColor(g.val), fontVariantNumeric: "tabular-nums", lineHeight: 1 }}>{g.val}</div>
                    <div style={{ fontSize: 10, color: "var(--ms-text-muted)", marginTop: 4, fontWeight: 600 }}>{g.label}</div>
                  </div>
                ))}
              </div>
              <div style={{ background: "var(--ms-bg-secondary)", borderRadius: 10, padding: 16, marginBottom: 16, borderLeft: "3px solid var(--ms-accent)", fontSize: 13, lineHeight: 1.6, color: "var(--ms-text-secondary)" }}>
                {data.summary}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <h4 style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700, color: "var(--ms-green)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Catalyseurs</h4>
                  {data.catalysts.length > 0 ? data.catalysts.map((c, i) => (
                    <div key={i} style={{ fontSize: 12, color: "var(--ms-text-secondary)", padding: "4px 0", display: "flex", gap: 6 }}><span style={{ color: "var(--ms-green)" }}>●</span> {c}</div>
                  )) : <div style={{ fontSize: 12, color: "var(--ms-text-muted)" }}>Aucun catalyseur majeur</div>}
                </div>
                <div>
                  <h4 style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700, color: "var(--ms-red)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Risques</h4>
                  {data.risks.length > 0 ? data.risks.map((r, i) => (
                    <div key={i} style={{ fontSize: 12, color: "var(--ms-text-secondary)", padding: "4px 0", display: "flex", gap: 6 }}><span style={{ color: "var(--ms-red)" }}>●</span> {r}</div>
                  )) : <div style={{ fontSize: 12, color: "var(--ms-text-muted)" }}>Aucun risque majeur</div>}
                </div>
              </div>
              {data.key_metrics && (
                <div style={{ marginTop: 16, padding: 14, background: "var(--ms-bg-secondary)", borderRadius: 10, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
                  {Object.entries(data.key_metrics).slice(0, 12).map(([k, v]) => (
                    <div key={k} style={{ textAlign: "center" }}>
                      <div style={{ fontSize: 10, color: "var(--ms-text-muted)" }}>{k}</div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ms-text)", fontVariantNumeric: "tabular-nums" }}>{v}</div>
                    </div>
                  ))}
                </div>
              )}
              <p style={{ margin: "16px 0 0", fontSize: 10, color: "var(--ms-text-muted)", textAlign: "center", fontStyle: "italic" }}>
                ⚠ Les scores IA sont générés à titre indicatif et ne constituent pas un conseil en investissement.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main App ───────────────────────────────────────────────────────────────
export default function MarketScreener() {
  const [stocks, setStocks] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [filtersApplied, setFiltersApplied] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({});
  const [filterOptions, setFilterOptions] = useState(null);
  const [showFilters, setShowFilters] = useState(true);
  const [sortKey, setSortKey] = useState("market_cap");
  const [sortDir, setSortDir] = useState("desc");
  const [activeView, setActiveView] = useState("performance");
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [hoveredRow, setHoveredRow] = useState(null);

  const searchTimer = useRef(null);

  // Fetch filter options on mount
  useEffect(() => {
    api("/filters").then(setFilterOptions).catch(() => {});
  }, []);

  // Build request body from state
  const buildRequest = useCallback(() => {
    const req = { sort_by: sortKey, sort_dir: sortDir, page, page_size: pageSize };
    if (search) req.search = search;
    for (const [key, val] of Object.entries(filters)) {
      if (val == null) continue;
      if (Array.isArray(val)) {
        req[key] = { min: val[0], max: val[1] };
      } else {
        req[key] = val;
      }
    }
    return req;
  }, [search, filters, sortKey, sortDir, page, pageSize]);

  // Fetch stocks from API
  const fetchStocks = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api("/screen", { method: "POST", body: JSON.stringify(buildRequest()) });
      setStocks(data.stocks);
      setTotal(data.total);
      setTotalPages(data.total_pages);
      setFiltersApplied(data.filters_applied);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [buildRequest]);

  // Trigger fetch on filter/sort/page change
  useEffect(() => { fetchStocks(); }, [fetchStocks]);

  // Debounced search
  const handleSearchChange = (val) => {
    setSearch(val);
    setPage(1);
  };

  const handleSort = useCallback((key) => {
    if (sortKey === key) { setSortDir(d => d === "asc" ? "desc" : "asc"); }
    else { setSortKey(key); setSortDir("desc"); }
    setPage(1);
  }, [sortKey]);

  const handlePresetApply = (preset) => {
    const f = {};
    for (const [k, v] of Object.entries(preset.filters)) {
      if (k === "sort_by" || k === "sort_dir") continue;
      if (typeof v === "object" && v !== null) {
        const rangeArr = [v.min ?? -Infinity, v.max ?? Infinity];
        f[k] = rangeArr;
      } else {
        f[k] = v;
      }
    }
    setFilters(f);
    if (preset.filters.sort_by) setSortKey(preset.filters.sort_by);
    if (preset.filters.sort_dir) setSortDir(preset.filters.sort_dir);
    setPage(1);
  };

  const activeCols = COLUMNS[activeView] || COLUMNS.performance;
  const activeFilterCount = Object.values(filters).filter(v => v != null).length;

  return (
    <div style={{ fontFamily: "'DM Sans', 'Segoe UI', system-ui, sans-serif", background: "var(--ms-bg)", color: "var(--ms-text)", minHeight: "100vh" }}>
      <style>{`
        :root {
          --ms-bg: #0b0e14; --ms-bg-secondary: #111622; --ms-bg-tertiary: #1a2030;
          --ms-bg-row-hover: #151c2b; --ms-border: #1e2740; --ms-border-light: #162035;
          --ms-text: #e8ecf4; --ms-text-secondary: #9aa5bb; --ms-text-muted: #586580;
          --ms-accent: #4f8ffa; --ms-accent-hover: #6aa1ff; --ms-green: #34d399;
          --ms-green-soft: #5cb88a; --ms-red: #f87171; --ms-red-soft: #e0725e;
          --ms-amber: #fbbf24; --ms-purple: #a78bfa;
        }
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--ms-bg); }
        ::-webkit-scrollbar-thumb { background: var(--ms-border); border-radius: 3px; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes scaleIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        @keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        @keyframes gradientShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
        .ms-header-glow { background: linear-gradient(135deg, #4f8ffa08, #a78bfa08, #34d39908); background-size: 400% 400%; animation: gradientShift 8s ease infinite; }
        .ms-view-tab { padding: 7px 14px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; white-space: nowrap; }
        .ms-view-tab-active { background: var(--ms-accent); color: white; }
        .ms-view-tab-inactive { background: transparent; color: var(--ms-text-muted); }
        .ms-view-tab-inactive:hover { background: var(--ms-bg-tertiary); color: var(--ms-text-secondary); }
        .ms-th { padding: 8px 10px; text-align: right; font-size: 10px; font-weight: 700; color: var(--ms-text-muted); text-transform: uppercase; letter-spacing: 0.06em; cursor: pointer; user-select: none; white-space: nowrap; border-bottom: 2px solid var(--ms-border); transition: color 0.15s; position: sticky; top: 0; background: var(--ms-bg-secondary); z-index: 2; }
        .ms-th:hover { color: var(--ms-accent); }
        .ms-th-active { color: var(--ms-accent); border-bottom-color: var(--ms-accent); }
        .ms-td { padding: 9px 10px; text-align: right; font-size: 12px; font-variant-numeric: tabular-nums; font-family: 'JetBrains Mono', monospace; font-weight: 500; white-space: nowrap; border-bottom: 1px solid var(--ms-border-light); }
        .ms-row { transition: background 0.1s; cursor: pointer; }
        .ms-row:hover { background: var(--ms-bg-row-hover) !important; }
        .ms-name-cell { position: sticky; left: 0; z-index: 1; background: inherit; padding: 9px 12px; border-bottom: 1px solid var(--ms-border-light); }
        .ms-name-th { position: sticky; left: 0; z-index: 3; background: var(--ms-bg-secondary); }
        .ms-search-input { background: var(--ms-bg-tertiary); border: 1px solid var(--ms-border); border-radius: 8px; padding: 8px 12px 8px 34px; font-size: 13px; color: var(--ms-text); width: 260px; outline: none; font-family: 'DM Sans', sans-serif; transition: border-color 0.2s; }
        .ms-search-input:focus { border-color: var(--ms-accent); }
        .ms-search-input::placeholder { color: var(--ms-text-muted); }
        .ms-loading-row td { padding: 6px 10px; }
        .ms-skeleton { height: 14px; border-radius: 4px; background: linear-gradient(90deg, var(--ms-bg-tertiary) 25%, var(--ms-border) 50%, var(--ms-bg-tertiary) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
      `}</style>

      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="ms-header-glow" style={{ padding: "20px 24px 0", borderBottom: "1px solid var(--ms-border)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 38, height: 38, borderRadius: 10, background: "linear-gradient(135deg, var(--ms-accent), var(--ms-purple))", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 800, fontSize: 16, boxShadow: "0 4px 20px rgba(79,143,250,0.3)" }}>MS</div>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 800, color: "var(--ms-text)", lineHeight: 1.1 }}>Market Screener</h1>
              <div style={{ fontSize: 11, color: "var(--ms-text-muted)", display: "flex", alignItems: "center", gap: 6 }}>
                <span>Screening augmenté par IA</span>
                <span style={{ background: "linear-gradient(90deg, var(--ms-accent), var(--ms-purple))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", fontWeight: 700, fontSize: 9, letterSpacing: "0.1em", textTransform: "uppercase" }}>POWERED BY AI</span>
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <div style={{ position: "relative" }}>
              <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--ms-text-muted)" }}><IconSearch /></span>
              <input type="text" className="ms-search-input" placeholder="Rechercher une action..." value={search} onChange={e => handleSearchChange(e.target.value)} />
            </div>
            <button className={`ms-view-tab ${showFilters ? "ms-view-tab-active" : "ms-view-tab-inactive"}`} onClick={() => setShowFilters(!showFilters)} style={{ display: "flex", alignItems: "center", gap: 6, border: "1px solid var(--ms-border)" }}>
              <IconFilter /> Filtres
              {activeFilterCount > 0 && <span style={{ background: "#fff", color: "var(--ms-accent)", borderRadius: 8, fontSize: 10, fontWeight: 700, padding: "0 6px", lineHeight: "16px" }}>{activeFilterCount}</span>}
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--ms-text-muted)", padding: "6px 12px", background: "var(--ms-bg-secondary)", borderRadius: 8, border: "1px solid var(--ms-border)" }}>
              {loading ? <div style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ms-amber)", animation: "pulse 0.8s infinite" }}/> : <div style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ms-green)", animation: "pulse 2s infinite" }}/>}
              {total} résultats
            </div>
          </div>
        </div>
        <PresetBar onApply={handlePresetApply} />
        <div style={{ display: "flex", gap: 4, overflowX: "auto", paddingBottom: 0 }}>
          {VIEW_PRESETS.map(v => (
            <button key={v.id} className={`ms-view-tab ${activeView === v.id ? "ms-view-tab-active" : "ms-view-tab-inactive"}`} onClick={() => setActiveView(v.id)}>
              {v.id === "ia" && <span style={{ marginRight: 4 }}>✦</span>}{v.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ───────────────────────────────────────────────── */}
      <div style={{ padding: "12px 24px 24px" }}>
        {showFilters && <FilterPanel filters={filters} setFilters={(f) => { setFilters(typeof f === 'function' ? f(filters) : f); setPage(1); }} filterOptions={filterOptions} onClose={() => setShowFilters(false)} />}
        {error && <div style={{ background: "var(--ms-red)15", border: "1px solid var(--ms-red)40", borderRadius: 8, padding: "10px 16px", marginBottom: 12, fontSize: 12, color: "var(--ms-red)" }}>Erreur API : {error} — les données proviennent du backend FastAPI.</div>}

        <div style={{ overflow: "auto", borderRadius: 10, border: "1px solid var(--ms-border)", background: "var(--ms-bg-secondary)", maxHeight: "calc(100vh - 280px)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 900 }}>
            <thead>
              <tr>
                <th className="ms-th ms-name-th" style={{ textAlign: "left", minWidth: 200 }} onClick={() => handleSort("name")}>
                  <div style={{ display: "flex", alignItems: "center", gap: 4 }}>Action {sortKey === "name" && <IconChevron dir={sortDir === "asc" ? "up" : "down"} />}</div>
                </th>
                <th className={`ms-th ${sortKey === "price" ? "ms-th-active" : ""}`} style={{ width: 90 }} onClick={() => handleSort("price")}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 4 }}>Cours {sortKey === "price" && <IconChevron dir={sortDir === "asc" ? "up" : "down"} />}</div>
                </th>
                <th className={`ms-th ${sortKey === "market_cap" ? "ms-th-active" : ""}`} style={{ width: 100 }} onClick={() => handleSort("market_cap")}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 4 }}>Cap. {sortKey === "market_cap" && <IconChevron dir={sortDir === "asc" ? "up" : "down"} />}</div>
                </th>
                {activeCols.map(col => (
                  <th key={col.key} className={`ms-th ${sortKey === col.sortKey ? "ms-th-active" : ""}`} style={{ width: col.width }} onClick={() => handleSort(col.sortKey)}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 4 }}>{col.label} {sortKey === col.sortKey && <IconChevron dir={sortDir === "asc" ? "up" : "down"} />}</div>
                  </th>
                ))}
                <th className="ms-th" style={{ width: 50 }}>IA</th>
              </tr>
            </thead>
            <tbody>
              {loading && stocks.length === 0 ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="ms-loading-row">
                    <td className="ms-name-cell" style={{ background: "var(--ms-bg-secondary)" }}><div className="ms-skeleton" style={{ width: 140 }}/></td>
                    <td className="ms-td"><div className="ms-skeleton" style={{ width: 60, marginLeft: "auto" }}/></td>
                    <td className="ms-td"><div className="ms-skeleton" style={{ width: 70, marginLeft: "auto" }}/></td>
                    {activeCols.map(c => <td key={c.key} className="ms-td"><div className="ms-skeleton" style={{ width: 50, marginLeft: "auto" }}/></td>)}
                    <td className="ms-td"><div className="ms-skeleton" style={{ width: 50, marginLeft: "auto" }}/></td>
                  </tr>
                ))
              ) : stocks.map((stock, idx) => (
                <tr key={stock.id} className="ms-row"
                  onMouseEnter={() => setHoveredRow(stock.id)} onMouseLeave={() => setHoveredRow(null)}
                  style={{ background: idx % 2 === 0 ? "transparent" : "var(--ms-bg-secondary)", opacity: loading ? 0.5 : 1, transition: "opacity 0.3s" }}
                  onClick={() => setSelectedTicker(stock.ticker)}>
                  <td className="ms-name-cell" style={{ background: hoveredRow === stock.id ? "var(--ms-bg-row-hover)" : "var(--ms-bg-secondary)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 32, height: 32, borderRadius: 8, background: `hsl(${(stock.id * 47) % 360}, 40%, 25%)`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: `hsl(${(stock.id * 47) % 360}, 60%, 70%)`, flexShrink: 0 }}>
                        {stock.name.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ms-text)", lineHeight: 1.2 }}>{stock.name}</div>
                        <div style={{ fontSize: 10, color: "var(--ms-text-muted)" }}>{stock.ticker} · {stock.sector}</div>
                      </div>
                    </div>
                  </td>
                  <td className="ms-td" style={{ fontWeight: 700, color: "var(--ms-text)" }}>{fmtPrice(stock.price)}</td>
                  <td className="ms-td" style={{ color: "var(--ms-text-secondary)", fontSize: 11 }}>{fmtCap(stock.marketCap)}</td>
                  {activeCols.map(col => {
                    const val = getNestedValue(stock, col.key);
                    if (col.isSignal) return <td key={col.key} className="ms-td"><SignalBadge signal={val} /></td>;
                    if (col.isScore) return <td key={col.key} className="ms-td"><ScoreBar value={val} /></td>;
                    return <td key={col.key} className="ms-td" style={{ color: col.color ? colorForValue(val, col.invertColor) : "var(--ms-text-secondary)" }}>{col.fmt(val)}</td>;
                  })}
                  <td className="ms-td" style={{ textAlign: "center" }}>
                    <button onClick={e => { e.stopPropagation(); setSelectedTicker(stock.ticker); }}
                      style={{ background: "linear-gradient(135deg, var(--ms-accent)20, var(--ms-purple)20)", border: "1px solid var(--ms-accent)30", borderRadius: 6, padding: "4px 8px", cursor: "pointer", color: "var(--ms-accent)", fontSize: 10, fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 3 }}
                      onMouseOver={e => { e.currentTarget.style.background = "var(--ms-accent)"; e.currentTarget.style.color = "white"; }}
                      onMouseOut={e => { e.currentTarget.style.background = "linear-gradient(135deg, var(--ms-accent)20, var(--ms-purple)20)"; e.currentTarget.style.color = "var(--ms-accent)"; }}>
                      <IconBrain /> Analyser
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && stocks.length === 0 && (
                <tr><td colSpan={activeCols.length + 4} style={{ textAlign: "center", padding: "48px 0", color: "var(--ms-text-muted)", fontSize: 14 }}>Aucune action ne correspond aux critères sélectionnés.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination page={page} totalPages={totalPages} total={total} onPageChange={setPage} />

        <div style={{ marginTop: 8, textAlign: "center", fontSize: 10, color: "var(--ms-text-muted)", lineHeight: 1.5 }}>
          Market Screener · Backend FastAPI + SQLite · {filtersApplied} filtre(s) appliqué(s)
          <br/>Frère de <span style={{ color: "var(--ms-accent)" }}>Market Insights</span> · Propulsé par l'intelligence artificielle
        </div>
      </div>

      {selectedTicker && <AIInsightPanel ticker={selectedTicker} onClose={() => setSelectedTicker(null)} />}
    </div>
  );
}
