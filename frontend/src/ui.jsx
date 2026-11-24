import React, { useEffect, useMemo, useRef, useState } from "react";

/* ───────────────────────── icons (24px stroke set) ───────────────────────── */
const P = {
  pulse: "M3 12h4l2-6 4 12 2-6h6", grid: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  chat: "M4 5h16v11H9l-5 4V5z", clock: "M12 7v5l3 2M12 3a9 9 0 100 18 9 9 0 000-18z",
  check: "M5 12.5l4.5 4.5L19 7.5", x: "M6 6l12 12M18 6L6 18", book: "M5 4h10a3 3 0 013 3v13H8a3 3 0 01-3-3V4zM8 20V7",
  users: "M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5M16 4.5a3.3 3.3 0 010 6.5M18 14.8c1.8.7 3 2.3 3.5 5.2",
  share: "M15 8a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100-6 3 3 0 000 6zM15 22a3 3 0 100-6 3 3 0 000 6zM8.7 10.5l4.6-2.6M8.7 13.5l4.6 2.6",
  shield: "M12 3l8 3v6c0 4.6-3.2 7.8-8 9-4.8-1.2-8-4.4-8-9V6l8-3zM8.5 12l2.5 2.5 4.5-5",
  send: "M4 12l16-8-6 16-2.5-6.5L4 12z", out: "M14 4h5v16h-5M10 8l-4 4 4 4M6 12h10", eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12zM12 15a3 3 0 100-6 3 3 0 000 6z",
  upload: "M12 16V4m0 0L7 9m5-5l5 5M4 20h16", down: "M12 4v12m0 0l-5-5m5 5l5-5M4 20h16", cog: "M12 15a3 3 0 100-6 3 3 0 000 6zM19 12l2-1-1-3-2.3.3-1.4-1.6.3-2.3-3-1-1 2h-2.2l-1-2-3 1 .3 2.3L6 7.3 3.7 7l-1 3 2 1v2l-2 1 1 3 2.3-.3 1.4 1.6-.3 2.3 3 1 1-2h2.2l1 2 3-1-.3-2.3 1.4-1.6 2.3.3 1-3-2-1v-2z",
  log: "M5 4h14v16H5zM8.5 9h7M8.5 13h7M8.5 17h4", spark: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16z",
  up: "M7 17L17 7M9 7h8v8", dn: "M7 7l10 10M17 9v8H9", search: "M11 18a7 7 0 100-14 7 7 0 000 14zM20 20l-4-4", plus: "M12 5v14M5 12h14",
  alert: "M12 4l9 16H3L12 4zM12 10v4M12 17.5v.5", bolt: "M13 3L5 13.5h6L10 21l8-10.5h-6L13 3z", flag: "M6 21V4m0 0h11l-2 4 2 4H6", refresh: "M20 11a8 8 0 10-2.3 5.7M20 5v6h-6",
  menu: "M4 7h16M4 12h16M4 17h16", file: "M7 3h7l5 5v13H7V3zM14 3v5h5", lock: "M6 11h12v9H6zM8.5 11V8a3.5 3.5 0 017 0v3",
  moon: "M20.5 14.5A8.5 8.5 0 019.5 3.5a8.6 8.6 0 1011 11z",
  wallet: "M3 6.5A2.5 2.5 0 015.5 4H20v16H5.5A2.5 2.5 0 013 17.5zM3 8h17M15.5 13h2",
  briefcase: "M3 8h18v12H3zM8 8V5h8v3M3 13h18M10 13v2h4v-2",
  calendar: "M4 6h16v15H4zM8 3v6M16 3v6M4 11h16",
  info: "M12 11v6M12 7h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  volume: "M4 10v4h4l5 4V6l-5 4H4zM17 9a5 5 0 010 6M19 6a9 9 0 010 12",
  sun: "M12 3v2m0 14v2M3 12h2m14 0h2M5.64 5.64l1.42 1.42m9.88 9.88 1.42 1.42m0-12.72-1.42 1.42m-9.88 9.88-1.42 1.42M16 12a4 4 0 11-8 0 4 4 0 018 0z",
};
export function Icon({ name, size = 18, className = "" }) {
  return (
    <svg className={`ico ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={P[name] || P.grid} /></svg>
  );
}

export function SandwichThemeToggle({ theme, onThemeChange, className = "" }) {
  const isDark = theme === "dark";
  return (
    <div className={`sandwich-toggle-wrap ${isDark ? "is-dark" : "is-light"} ${className}`}>
      <button
        type="button"
        className="sandwich-toggle-btn"
        onClick={() => onThemeChange(isDark ? "light" : "dark")}
        title={`Current: ${isDark ? "Dark" : "Light"} mode. Click to switch to ${isDark ? "Light" : "Dark"} mode.`}
        aria-label={`Toggle theme. Current: ${theme}`}
        aria-pressed={isDark}
      >
        <span className="half-tri tri-dark" aria-hidden="true">
          <span className="tri-text">DARK</span>
        </span>
        <span className="half-tri tri-light" aria-hidden="true">
          <span className="tri-text">LIGHT</span>
        </span>
        <span className="sandwich-seam" aria-hidden="true" />
        <span className="sandwich-indicator" aria-hidden="true" />
      </button>
    </div>
  );
}

/* ───────────────────────── hooks ───────────────────────── */
const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Polls `fn` every `ms` (paused while the tab is hidden). Returns data, error, loading, refresh, lastUpdated, tick. */
export function useLive(fn, ms, deps = []) {
  const [state, setState] = useState({ data: null, error: "", loading: true, updated: null, tick: 0 });
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const run = useRef(() => {});
  useEffect(() => {
    let alive = true, timer;
    run.current = async () => {
      try {
        const data = await fnRef.current();
        if (alive) setState((s) => ({ data, error: "", loading: false, updated: new Date(), tick: s.tick + 1 }));
      } catch (e) {
        if (alive) setState((s) => ({ ...s, error: e.message, loading: false }));
      }
    };
    const loop = () => { if (!document.hidden) run.current(); timer = setTimeout(loop, ms); };
    setState((s) => ({ ...s, loading: true }));
    loop();
    const vis = () => { if (!document.hidden) run.current(); };
    document.addEventListener("visibilitychange", vis);
    return () => { alive = false; clearTimeout(timer); document.removeEventListener("visibilitychange", vis); };
  }, [ms, ...deps]);
  return { ...state, refresh: () => run.current() };
}

/** Eases a number or an array of numbers toward its target so charts glide when data changes. */
export function useTween(target, ms = 650) {
  const [val, setVal] = useState(target);
  const from = useRef(target);
  const raf = useRef(0);
  const key = JSON.stringify(target);
  useEffect(() => {
    if (reduced()) { setVal(target); from.current = target; return; }
    const start = performance.now(), a = from.current, b = target;
    const mix = (x, y, t) => (Array.isArray(y) ? y.map((v, i) => mix(x?.[i] ?? 0, v, t)) : (x ?? 0) + (y - (x ?? 0)) * t);
    const step = (now) => {
      const t = Math.min(1, (now - start) / ms), e = 1 - Math.pow(1 - t, 3);
      const next = mix(a, b, e);
      from.current = next; setVal(next);
      if (t < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [key]); // eslint-disable-line
  return val;
}

export function useWidth() {
  const ref = useRef(null);
  const [w, setW] = useState(640);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(260, Math.floor(e.contentRect.width))));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

/* ───────────────────────── small formatters ───────────────────────── */
export const fmt = (n) => (n >= 10000 ? `${(n / 1000).toFixed(1)}k` : Math.round(n).toLocaleString());
export const ms = (n) => (n >= 1000 ? `${(n / 1000).toFixed(2)}s` : `${Math.round(n)}ms`);
export const delta = (cur, prev) => (!prev ? (cur ? 100 : 0) : ((cur - prev) / prev) * 100);
export const shortDate = (d) => new Date(d + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
export const ago = (ts) => {
  const s = Math.max(0, (Date.now() - new Date(ts.replace(" ", "T") + "Z").getTime()) / 1000);
  return s < 60 ? "just now" : s < 3600 ? `${Math.floor(s / 60)}m ago` : s < 86400 ? `${Math.floor(s / 3600)}h ago` : `${Math.floor(s / 86400)}d ago`;
};
export const TOPIC_COLORS = { refund: "#0E9F8E", attendance: "#4C5BD4", programme: "#C9A24D", support: "#E4572E", assessment: "#8E5BD9", freelancing: "#2F8FD8", other: "#8A94A6" };

export function Count({ value, suffix = "", decimals = 0 }) {
  const v = useTween(Number(value) || 0);
  return <>{decimals ? v.toFixed(decimals) : Math.round(v).toLocaleString()}{suffix}</>;
}

/* ───────────────────────── charts ───────────────────────── */
export function Sparkline({ values, color = "currentColor", height = 34 }) {
  const v = useTween(values || []);
  if (!values?.length) return null;
  const w = 120, max = Math.max(...v, 1), min = Math.min(...v, 0);
  const pts = v.map((y, i) => [(i / Math.max(v.length - 1, 1)) * w, height - 3 - ((y - min) / (max - min || 1)) * (height - 8)]);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  const last = pts[pts.length - 1] || [0, 0];
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" style={{ color }} aria-hidden="true">
      <path d={`${d} L${w} ${height} L0 ${height}Z`} fill="currentColor" opacity=".12" />
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
      <circle cx={last[0]} cy={last[1]} r="2.4" fill="currentColor" />
    </svg>
  );
}

/** Stacked area chart with hover crosshair. series = [{key,label,color,values}] */
export function AreaChart({ labels, series, height = 250, live }) {
  const [ref, W] = useWidth();
  const [hover, setHover] = useState(null);
  const animated = useTween(series.map((s) => s.values));
  const H = height, m = { t: 14, r: 12, b: 26, l: 34 };
  const n = labels.length, iw = W - m.l - m.r, ih = H - m.t - m.b;
  const totals = labels.map((_, i) => animated.reduce((a, s) => a + (s[i] || 0), 0));
  const niceMax = (() => { const mx = Math.max(...totals, 4); const p = Math.pow(10, Math.floor(Math.log10(mx))); return Math.ceil(mx / p) * p; })();
  const x = (i) => m.l + (n === 1 ? iw / 2 : (i / (n - 1)) * iw), y = (v) => m.t + ih - (v / niceMax) * ih;
  const layers = useMemo(() => {
    const base = Array(n).fill(0);
    return animated.map((vals) => {
      const lo = base.slice(), hi = vals.map((v, i) => (base[i] += v || 0));
      return { lo, hi: hi.slice() };
    });
  }, [animated, n]);
  const smooth = (pts) => pts.map((p, i) => {
    if (!i) return `M${p[0]} ${p[1]}`;
    const q = pts[i - 1], cx = (q[0] + p[0]) / 2;
    return `C${cx} ${q[1]} ${cx} ${p[1]} ${p[0]} ${p[1]}`;
  }).join(" ");
  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const i = Math.round(((e.clientX - r.left - m.l) / iw) * (n - 1));
    setHover(Math.min(n - 1, Math.max(0, i)));
  };
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(niceMax * t));
  const step = Math.ceil(n / Math.max(2, Math.floor(iw / 70)));
  return (
    <div className="chart-wrap" ref={ref}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} onMouseMove={onMove} onMouseLeave={() => setHover(null)} role="img"
        aria-label="Questions per day, stacked by outcome">
        {ticks.map((t) => (<g key={t}><line x1={m.l} x2={W - m.r} y1={y(t)} y2={y(t)} className="grid" /><text x={m.l - 8} y={y(t) + 4} className="axis" textAnchor="end">{t}</text></g>))}
        {layers.map((l, k) => {
          const top = l.hi.map((v, i) => [x(i), y(v)]), bot = l.lo.map((v, i) => [x(i), y(v)]).reverse();
          return <path key={series[k].key} d={`${smooth(top)} L${bot[0][0]} ${bot[0][1]} ${smooth(bot).replace(/^M[^C]*/, "")} Z`} fill={series[k].color} opacity=".88" />;
        })}
        {labels.map((l, i) => i % step === 0 && <text key={l} x={x(i)} y={H - 6} className="axis" textAnchor="middle">{shortDate(l)}</text>)}
        {live && n > 0 && <g className="live-dot" transform={`translate(${x(n - 1)} ${y(totals[n - 1])})`}><circle r="9" className="ring" /><circle r="4" /></g>}
        {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={m.t} y2={H - m.b} className="cross" />}
      </svg>
      {hover !== null && (
        <div className="tip" style={{ left: Math.min(Math.max(x(hover), 90), W - 90) }}>
          <b>{shortDate(labels[hover])}</b>
          {series.map((s) => <div key={s.key}><i style={{ background: s.color }} />{s.label}<span>{s.values[hover] ?? 0}</span></div>)}
        </div>
      )}
    </div>
  );
}

export function Donut({ items, size = 170, centerLabel = "questions" }) {
  const vals = useTween(items.map((i) => i.value));
  const total = vals.reduce((a, b) => a + b, 0) || 1, r = 62, c = 2 * Math.PI * r;
  let off = 0;
  return (
    <div className="donut" style={{ width: size }}>
      <svg viewBox="0 0 160 160" width={size} height={size} role="img" aria-label="Share by topic">
        <circle cx="80" cy="80" r={r} fill="none" className="donut-track" strokeWidth="16" />
        {items.map((it, i) => {
          const len = (vals[i] / total) * c, el = (
            <circle key={it.label} cx="80" cy="80" r={r} fill="none" stroke={it.color} strokeWidth="16"
              strokeDasharray={`${Math.max(len - 2, 0)} ${c}`} strokeDashoffset={-off} transform="rotate(-90 80 80)" />);
          off += len; return el;
        })}
      </svg>
      <div className="donut-center"><strong><Count value={items.reduce((a, b) => a + b.value, 0)} /></strong><span>{centerLabel}</span></div>
    </div>
  );
}

export function Ring({ value, label, color = "var(--teal)", size = 120 }) {
  const v = useTween(value), r = 48, c = 2 * Math.PI * r;
  return (
    <div className="ring-meter" style={{ width: size, height: size }}>
      <svg viewBox="0 0 120 120" width={size} height={size}>
        <circle cx="60" cy="60" r={r} className="donut-track" fill="none" strokeWidth="9" />
        <circle cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={`${(v / 100) * c} ${c}`} transform="rotate(-90 60 60)" />
      </svg>
      <div><strong>{Math.round(v)}%</strong><span>{label}</span></div>
    </div>
  );
}

export function Bars({ items, color = "var(--teal)", format = fmt, max }) {
  const vals = useTween(items.map((i) => i.value));
  const top = max || Math.max(...items.map((i) => i.value), 1);
  return (
    <ul className="bars">
      {items.map((it, i) => (
        <li key={it.label}>
          <div className="bars-head"><span title={it.title}>{it.label}</span><b>{format(it.value)}</b></div>
          <div className="bars-track"><i style={{ width: `${(vals[i] / top) * 100}%`, background: it.color || color }} /></div>
          {it.note && <small>{it.note}</small>}
        </li>
      ))}
    </ul>
  );
}

export function Columns({ items, height = 120, color = "var(--ink)" }) {
  const vals = useTween(items.map((i) => i.value));
  const top = Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="columns" style={{ height }}>
      {items.map((it, i) => (
        <div key={it.label} className="col"><span className="col-n">{it.value}</span>
          <i style={{ height: `${Math.max(2, (vals[i] / top) * (height - 38))}px`, background: color }} /><em>{it.label}</em></div>
      ))}
    </div>
  );
}

export function Heatmap({ grid }) {
  const flat = grid.flat(), max = Math.max(...flat, 1);
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  return (
    <div className="heat" role="img" aria-label="Question volume by weekday and hour (UTC)">
      {grid.map((row, d) => (
        <div className="heat-row" key={d}><span>{days[d]}</span>
          <div>{row.map((v, h) => <i key={h} title={`${days[d]} ${String(h).padStart(2, "0")}:00 UTC: ${v}`} style={{ "--a": v ? 0.14 + (v / max) * 0.86 : 0 }} />)}</div>
        </div>
      ))}
      <div className="heat-axis"><span /><div>{[0, 6, 12, 18, 23].map((h) => <em key={h} style={{ left: `${(h / 23) * 100}%` }}>{String(h).padStart(2, "0")}</em>)}</div></div>
    </div>
  );
}

/** Relative % change by default; `points` shows the absolute difference for metrics that are already percentages. */
export function Delta({ cur, prev, invert = false, points = false }) {
  if (!prev && !cur) return <span className="delta flat">no change</span>;
  if (!points && !prev) return <span className="delta flat">new</span>;
  const d = points ? cur - prev : delta(cur, prev), good = invert ? d <= 0 : d >= 0;
  return <span className={`delta ${Math.abs(d) < 0.5 ? "flat" : good ? "good" : "bad"}`}><Icon name={d >= 0 ? "up" : "dn"} size={12} />{Math.abs(d).toFixed(points ? 1 : 0)}{points ? " pt" : "%"}</span>;
}
