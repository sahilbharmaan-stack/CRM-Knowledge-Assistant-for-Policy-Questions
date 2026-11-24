import React, { useEffect, useRef, useState } from "react";
import { analytics, simulateTraffic } from "./api";
import { AreaChart, Bars, Columns, Count, Delta, Donut, Heatmap, Icon, Ring, Sparkline, TOPIC_COLORS, ago, fmt, ms, useLive } from "./ui.jsx";

const RANGES = [7, 14, 30, 90];
const STATUS_TONE = { answered: "ok", abstained: "warn", api_error: "bad", rejected: "bad", received: "idle" };

function Kpi({ label, value, suffix, decimals, prev, cur, invert, points, noDelta, spark, color, note, icon }) {
  return (
    <article className="kpi">
      <header><span>{label}</span><Icon name={icon} size={16} /></header>
      <strong><Count value={value} suffix={suffix} decimals={decimals} /></strong>
      <footer>{!noDelta && <Delta cur={cur} prev={prev} invert={invert} points={points} />}<small>{note}</small></footer>
      <Sparkline values={spark} color={color} />
    </article>
  );
}

function exportCsv(d) {
  const rows = [["date", "questions", "answered", "abstained", "api_error", "helpful", "not_helpful", "avg_latency_ms"],
    ...d.daily.map((r) => [r.date, r.total, r.answered, r.abstained, r.api_error, r.helpful, r.not_helpful, r.latency_ms])];
  const csv = rows.map((r) => r.join(",")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = `crm-analytics-${d.days}d-${d.generated_at.slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function Analytics({ role, onNavigate }) {
  const [days, setDays] = useState(14);
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState(false);
  const [simulateError, setSimulateError] = useState("");
  const [, force] = useState(0);
  const { data: d, error, loading, updated, refresh } = useLive(() => analytics(days), 8000, [days]);
  const seen = useRef("");

  useEffect(() => { const t = setInterval(() => force((x) => x + 1), 1000); return () => clearInterval(t); }, []);
  useEffect(() => {
    if (!d) return;
    if (seen.current && seen.current !== d.fingerprint) { setFlash(true); setTimeout(() => setFlash(false), 1600); }
    seen.current = d.fingerprint;
  }, [d?.fingerprint]);

  const simulate = async () => {
    setBusy(true);
    setSimulateError("");
    try { await simulateTraffic(4); await refresh(); }
    catch (e) { setSimulateError(e.message); }
    finally { setBusy(false); }
  };
  const secs = updated ? Math.round((Date.now() - updated.getTime()) / 1000) : null;
  const isAdmin = role === "administrator";

  if (!d) return (
    <div className="view"><div className="skeleton-grid">{Array.from({ length: 5 }).map((_, i) => <i key={i} />)}</div>
      {error && <div className="banner bad" role="alert">{error}</div>}{loading && <p className="muted">Reading live data…</p>}</div>
  );

  const c = d.current, p = d.previous, daily = d.daily;
  const col = (k) => daily.map((x) => x[k]);
  const personal = d.scope === "personal";
  const topicItems = d.topics.map((t) => ({ label: t.topic, value: t.count, color: TOPIC_COLORS[t.topic] || "#8A94A6" }));
  const r = d.review, rTotal = r.pending + r.approved + r.rejected || 1;
  const empty = c.total === 0;

  return (
    <div className="view analytics">
      <header className="view-head">
        <div>
          <h1>{personal ? "Your activity" : "Policy intelligence"}</h1>
          <p>{personal ? "Questions you asked, how they were answered, and what reviewers decided." : "Every number below is computed from the live database and moves the moment someone asks, reviews or rates."}</p>
        </div>
        <div className="head-tools">
          <span className={`live-pill ${flash ? "flash" : ""} ${error ? "down" : ""}`} aria-live="polite">
            <i />{error ? "Connection lost" : flash ? "New data" : "Live"}<small>{secs === null ? "" : secs < 2 ? "now" : `${secs}s ago`}</small>
          </span>
          <div className="seg" role="group" aria-label="Date range">
            {RANGES.map((n) => <button key={n} className={days === n ? "on" : ""} onClick={() => setDays(n)}>{n}d</button>)}
          </div>
          <button className="btn ghost" onClick={refresh} aria-label="Refresh now"><Icon name="refresh" size={16} /></button>
          <button className="btn ghost" onClick={() => exportCsv(d)}><Icon name="down" size={16} />CSV</button>
          {isAdmin && <button className="btn gold" onClick={simulate} disabled={busy}><Icon name="bolt" size={16} />{busy ? "Sending…" : "Send live traffic"}</button>}
        </div>
      </header>

      {simulateError && <div className="banner bad" role="alert">{simulateError}</div>}
      {error && <div className="banner bad" role="alert">{error} — showing the last good snapshot.</div>}
      {empty && (
        <div className="banner info">No questions in the last {days} days yet. {isAdmin ? "Use “Send live traffic” to watch the charts move, or ask a question." : "Ask your first question and this page fills in."}
          <button className="link" onClick={() => onNavigate("ask")}>Ask a question</button></div>
      )}

      <section className="kpi-row" aria-label="Key metrics">
        <Kpi icon="chat" label="Questions" value={c.total} cur={c.total} prev={p.total} spark={col("total")} color="var(--indigo)" note={`vs previous ${days}d`} />
        <Kpi icon="check" label="Answer rate" value={c.answer_rate} decimals={1} suffix="%" points cur={c.answer_rate} prev={p.answer_rate} spark={daily.map((x) => (x.total ? (x.answered / x.total) * 100 : 0))} color="var(--teal)" note={`${c.abstained} abstained`} />
        <Kpi icon="bolt" label="Avg response" value={d.latency.avg} suffix=" ms" cur={d.latency.avg} prev={p.avg_latency_ms} invert spark={col("latency_ms")} color="var(--indigo)" note={`p95 ${ms(d.latency.p95)}`} />
        <Kpi icon="spark" label="Helpful rate" value={c.helpful_rate} decimals={1} suffix="%" points cur={c.helpful_rate} prev={p.helpful_rate} spark={daily.map((x) => (x.helpful + x.not_helpful ? (x.helpful / (x.helpful + x.not_helpful)) * 100 : 0))} color="var(--brass)" note={`${c.helpful + c.not_helpful} ratings`} />
        <Kpi icon="clock" label="Awaiting review" value={r.pending} noDelta color="var(--coral)" note={`${r.escalated} escalated · ${r.avg_turnaround_min >= 90 ? (r.avg_turnaround_min / 60).toFixed(1) + " h" : Math.round(r.avg_turnaround_min) + " min"} avg wait`} />
      </section>

      <div className="grid g-main">
        <section className="card">
          <header className="card-head"><div><h2>Question volume</h2><p>Daily questions by outcome</p></div>
            <ul className="legend"><li><i style={{ background: "var(--teal)" }} />Answered</li><li><i style={{ background: "var(--brass)" }} />Abstained</li><li><i style={{ background: "var(--coral)" }} />Error</li></ul></header>
          <AreaChart live labels={daily.map((x) => x.date)} series={[
            { key: "a", label: "Answered", color: "var(--teal)", values: col("answered") },
            { key: "b", label: "Abstained", color: "var(--brass)", values: col("abstained") },
            { key: "e", label: "API error", color: "var(--coral)", values: col("api_error") }]} />
        </section>
        <section className="card">
          <header className="card-head"><div><h2>What people ask about</h2><p>Share of questions by topic</p></div></header>
          <div className="donut-row">
            <Donut items={topicItems.length ? topicItems : [{ label: "none", value: 0, color: "#DDE2E8" }]} />
            <ul className="topic-list">{d.topics.map((t) => (
              <li key={t.topic}><i style={{ background: TOPIC_COLORS[t.topic] || "#8A94A6" }} /><span>{t.topic}</span><b>{Math.round((t.count / (c.total || 1)) * 100)}%</b></li>))}</ul>
          </div>
        </section>
      </div>

      <div className="grid g-three">
        <section className="card">
          <header className="card-head"><div><h2>Busiest hours</h2><p>Weekday × hour, UTC</p></div></header>
          <Heatmap grid={d.heatmap} />
        </section>
        <section className="card">
          <header className="card-head"><div><h2>Most relied-on policies</h2><p>Top retrieved document per question</p></div></header>
          {d.top_docs.length ? <Bars items={d.top_docs.map((x) => ({ label: x.doc_code, title: x.title, value: x.uses, note: `${x.title} · v${x.version}` }))} /> : <p className="muted pad">No retrievals yet.</p>}
        </section>
        <section className="card">
          <header className="card-head"><div><h2>Response time</h2><p>p50 {ms(d.latency.p50)} · p95 {ms(d.latency.p95)}</p></div></header>
          <Columns items={d.latency.histogram.map((h) => ({ label: h.label, value: h.count }))} height={170} color="var(--indigo)" />
        </section>
      </div>

      <div className="grid g-three">
        <section className="card">
          <header className="card-head"><div><h2>Review pipeline</h2><p>Human sign-off on every answer</p></div><button className="link" onClick={() => onNavigate("review")}>Open queue</button></header>
          <div className="stack" role="img" aria-label="Review status split">
            <i style={{ flex: r.approved / rTotal, background: "var(--teal)" }} /><i style={{ flex: r.pending / rTotal, background: "var(--brass)" }} /><i style={{ flex: r.rejected / rTotal, background: "var(--coral)" }} />
          </div>
          <ul className="kv"><li><i style={{ background: "var(--teal)" }} />Approved<b>{fmt(r.approved)}</b></li><li><i style={{ background: "var(--brass)" }} />Pending<b>{fmt(r.pending)}</b></li>
            <li><i style={{ background: "var(--coral)" }} />Rejected<b>{fmt(r.rejected)}</b></li><li><i style={{ background: "var(--ink)" }} />Avg turnaround<b>{r.avg_turnaround_min >= 90 ? `${(r.avg_turnaround_min / 60).toFixed(1)} h` : `${Math.round(r.avg_turnaround_min)} min`}</b></li></ul>
        </section>
        <section className="card center">
          <header className="card-head"><div><h2>Grounding quality</h2><p>Answered with a policy source</p></div></header>
          <Ring value={c.answer_rate} label="answered" />
          <p className="muted small">When the policy has no answer the assistant abstains instead of guessing.</p>
        </section>
        <section className="card">
          <header className="card-head"><div><h2>{personal ? "Model usage" : "Who is asking"}</h2><p>{personal ? "Provider and model per answer" : "Most active accounts"}</p></div></header>
          {personal || !d.people.length
            ? <ul className="kv">{d.providers.map((x) => <li key={x.provider + x.model}><i style={{ background: "var(--indigo)" }} />{x.provider}<small>{x.model}</small><b>{fmt(x.count)}</b></li>)}{!d.providers.length && <li className="muted">No answers yet.</li>}</ul>
            : <Bars color="var(--ink)" items={d.people.map((x) => ({ label: x.name, value: x.questions, note: `${x.answered} answered · ${ago(x.last_seen)}` }))} />}
        </section>
      </div>

      <section className="card">
        <header className="card-head"><div><h2>Live activity</h2><p>Newest questions across {personal ? "your account" : "the workspace"}</p></div><span className="muted small">refreshes every 8 s</span></header>
        <ul className="feed">
          {d.live.map((x) => (
            <li key={x.id}>
              <span className={`dot ${STATUS_TONE[x.status] || "idle"}`} />
              <div><b>{x.query_text}</b><small>{x.username} · {x.topic || "other"}{x.latency_ms ? ` · ${ms(x.latency_ms)}` : ""}</small></div>
              <span className={`tag ${STATUS_TONE[x.status] || "idle"}`}>{x.status.replace("_", " ")}</span><time>{ago(x.created_at)}</time>
            </li>))}
          {!d.live.length && <li className="muted pad">Nothing yet.</li>}
        </ul>
      </section>
    </div>
  );
}
