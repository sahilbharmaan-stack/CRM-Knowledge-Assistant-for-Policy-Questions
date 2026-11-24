import React, { useEffect, useRef, useState } from "react";
import { Icon, TOPIC_COLORS, ago, ms } from "./ui.jsx";

export const QUESTION_GROUPS = [
  { title: "Refunds & payments", icon: "wallet", questions: [
    "What is the refund policy if I withdraw from a programme?",
    "Am I eligible for a refund after attending some classes?",
    "How long does an approved refund take to process?",
    "What should I do if my fee payment is not reflecting?",
  ]},
  { title: "Freelancing & projects", icon: "briefcase", questions: [
    "Am I eligible for a freelancing project after completing the course?",
    "Does submitting the Core Project guarantee a freelancing assignment?",
    "What are the eligibility criteria for receiving a client project?",
    "What happens if I miss a project deadline?",
  ]},
  { title: "Attendance & leave", icon: "calendar", questions: [
    "What is the minimum attendance requirement?",
    "How can I check my attendance record?",
    "Can I request leave for a medical or personal reason?",
    "What happens if my attendance falls below the required percentage?",
  ]},
  { title: "Learning & support", icon: "book", questions: [
    "What should I do if I miss a class?",
    "How can I get help from my mentor or counsellor?",
    "What are the requirements to receive a course completion certificate?",
    "How do I raise a complaint or escalate an unresolved issue?",
  ]},
];
const REVIEW_LABEL = { approved: "Approved by reviewer", rejected: "Rejected", pending_review: "Awaiting human review" };

export function AnswerCard({ item, role, onReview, onFeedback, onEscalate }) {
  const [open, setOpen] = useState(false);
  const cites = item.citations?.length ? item.citations : [];
  const passages = item.passages || [];
  const abstained = item.query_status === "abstained" || item.abstained;
  const errored = item.query_status === "api_error";
  const canReview = ["administrator", "policy_manager", "reviewer"].includes(role) && item.review_status === "pending_review";
  const conf = item.topic_confidence != null ? Math.round(item.topic_confidence * 100) : null;
  return (
    <article className={`qa ${abstained ? "abstained" : ""} ${errored ? "errored" : ""}`}>
      <div className="qa-q"><span className="who">{(item.username || "You").slice(0, 2).toUpperCase()}</span><p>{item.query_text}</p>{item.created_at && <time>{ago(item.created_at)}</time>}</div>
      <div className="qa-a">
        <div className="qa-meta">
          {item.topic && <span className="topic" style={{ "--c": TOPIC_COLORS[item.topic] || "#8A94A6" }}>{item.topic}</span>}
          {conf !== null && <span className="conf" title="Topic classifier confidence"><i style={{ width: `${conf}%` }} />{conf}%</span>}
          {item.provider && <span className="mono">{item.provider} · {item.model}</span>}
          {item.latency_ms != null && <span className="mono">{ms(item.latency_ms)}</span>}
        </div>
        {item.answer_text || item.answer ? <p className="qa-text">{item.answer_text || item.answer}</p>
          : <p className="qa-text muted">{item.message || (errored ? "The model service did not respond. The retrieved policy passages are listed below." : abstained ? "The approved policies do not contain an answer to this. Please check with a policy manager." : "No answer was generated.")}</p>}
        {abstained && <div className="note warn"><Icon name="alert" size={15} />Abstained: no approved policy text supports an answer, so nothing was guessed.</div>}
        {errored && <div className="note bad"><Icon name="alert" size={15} />API error recorded. You can ask again.</div>}
        {(cites.length > 0 || passages.length > 0) && (
          <div className="cites">
            {(cites.length ? cites : passages.slice(0, 3)).map((c, i) => (
              <button key={`${c.chunk_id}-${i}`} className="chip" onClick={() => setOpen(!open)} title="Show retrieved passages">
                <Icon name="file" size={13} /><b>{c.doc_code}</b><span>v{c.version}</span>{c.heading && <em>{c.heading}</em>}
              </button>))}
          </div>)}
        {open && passages.length > 0 && (
          <ol className="passages">{passages.map((p) => <li key={p.chunk_id}><b>{p.doc_code} v{p.version}</b> {p.heading}<span>relevance {(p.score * 100).toFixed(0)}</span></li>)}</ol>)}
        <footer className="qa-foot">
          <span className={`status ${item.review_status || "pending_review"}`}><i />{REVIEW_LABEL[item.review_status || "pending_review"]}</span>
          <div className="qa-actions">
            {role === "counsellor" && item.review_status === "approved" && ["helpful", "not_helpful"].map((f) => (
              <button key={f} className={`btn mini ${item.feedback === f ? "on" : ""}`} onClick={() => onFeedback(item.answer_id, f)}>
                <Icon name={f === "helpful" ? "check" : "x"} size={14} />{f === "helpful" ? "Helpful" : "Not helpful"}</button>))}
            {role === "counsellor" && onEscalate && !item.escalated && item.answer_id && (
              <button className="btn mini" onClick={() => onEscalate(item.answer_id)}><Icon name="flag" size={14} />Escalate</button>)}
            {item.escalated && <span className="tag warn">escalated</span>}
            {canReview && <>
              <button className="btn mini bad" onClick={() => onReview(item.answer_id, "rejected")}><Icon name="x" size={14} />Reject</button>
              <button className="btn mini ok" onClick={() => onReview(item.answer_id, "approved")}><Icon name="check" size={14} />Approve</button></>}
          </div>
        </footer>
      </div>
    </article>
  );
}

export function AskView({ items, role, loading, error, onAsk, onReview, onFeedback, onEscalate }) {
  const [text, setText] = useState("");
  const ref = useRef(null), endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [items.length, loading]);
  const send = async (e) => {
    e?.preventDefault();
    const q = text.trim();
    if (!q || loading) return;
    const succeeded = await onAsk(q);
    if (succeeded !== false) setText("");
    ref.current?.focus();
  };
  return (
    <div className="view ask">
      <header className="view-head"><div><h1>Ask a policy question</h1><p>Answers are written only from approved policy text, cite the document and version, and wait for human review.</p></div>
        <span className="tag ok"><Icon name="shield" size={13} />Human review required</span></header>
      <div className="ask-scroll">
        <section className="question-starters glass-panel floating-section" aria-label="Popular questions">
          <div className="question-starters-head"><div><h2>Explore common questions</h2><p>Choose a prompt to start. Answers are checked against approved CRM policies.</p></div><span className="tag glass-tag">Quick prompts</span></div>
          <div className="question-groups">
            {QUESTION_GROUPS.map((group, gIdx) => <section className="question-group glass-card" key={group.title} style={{ animationDelay: `${gIdx * 0.15}s` }}>
              <h3><Icon name={group.icon} size={16} />{group.title}</h3>
              <div className="suggest">{group.questions.map((question, qIdx) => <button key={question} type="button" className="glass-suggestion-btn floating-item" style={{ animationDelay: `${(gIdx * 4 + qIdx) * 0.08}s` }} onClick={() => { setText(question); ref.current?.focus(); }}><span className="sug-text">{question}</span><Icon name="up" size={13} className="sug-ico" /></button>)}</div>
            </section>)}
          </div>
          <p className="prompt-note"><Icon name="info" size={14} />These are suggested questions, not policy decisions. Eligibility and outcomes depend on the approved policy and your records.</p>
        </section>
        {items.slice(0, 15).reverse().map((it) => <AnswerCard key={it.answer_id || it.query_id} item={it} role={role} onReview={onReview} onFeedback={onFeedback} onEscalate={onEscalate} />)}
        {loading && <div className="thinking" role="status"><i /><i /><i />Searching approved policies…</div>}
        <div className="ask-end" ref={endRef} />
      </div>
      {error && <div className="banner bad" role="alert">{error}</div>}
      <form className="composer glass-composer" onSubmit={send}>
        <textarea ref={ref} value={text} rows={2} maxLength={2000} disabled={loading} placeholder="Ask about refunds, attendance, programmes, support…" aria-label="Your question"
          onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) send(e); }} />
        <button className="send" disabled={!text.trim() || loading} aria-label="Send question"><Icon name="send" size={18} /></button>
      </form>
    </div>
  );
}

export function HistoryView({ items, role, onFeedback, onEscalate, onReview }) {
  const [q, setQ] = useState(""), [st, setSt] = useState("");
  const rows = items.filter((i) => (!st || i.query_status === st) && (!q || i.query_text.toLowerCase().includes(q.toLowerCase())));
  return (
    <div className="view">
      <header className="view-head"><div><h1>Question history</h1><p>{items.length} saved answers with their original policy citations.</p></div></header>
      <div className="toolbar"><div className="search"><Icon name="search" size={16} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search questions…" aria-label="Search history" /></div>
        <select value={st} onChange={(e) => setSt(e.target.value)} aria-label="Filter by status"><option value="">All outcomes</option><option value="answered">Answered</option><option value="abstained">Abstained</option><option value="api_error">API error</option></select></div>
      <div className="stack-list">{rows.map((i) => <AnswerCard key={i.query_id} item={i} role={role} onFeedback={onFeedback} onEscalate={onEscalate} onReview={onReview} />)}
        {!rows.length && <div className="empty small"><h2>Nothing matches</h2><p>Change the search or filter.</p></div>}</div>
    </div>
  );
}

export function ReviewView({ items, onReview }) {
  return (
    <div className="view">
      <header className="view-head"><div><h1>Review queue</h1><p>Nothing reaches a counsellor as approved until a person checks it against the cited policy.</p></div><span className="tag warn">{items.length} pending</span></header>
      <div className="stack-list">{items.map((i) => <AnswerCard key={i.answer_id} item={i} role="reviewer" onReview={onReview} />)}
        {!items.length && <div className="empty"><Icon name="check" size={30} /><h2>Queue clear</h2><p>No answers are waiting for review.</p></div>}</div>
    </div>
  );
}

export function KnowledgeView({ docs, role, search, setSearch, status, setStatus, onReload, onSubmit, onDecide, canDecide }) {
  const editor = ["administrator", "policy_manager", "reviewer"].includes(role);
  const counts = docs.reduce((a, d) => ({ ...a, [d.status]: (a[d.status] || 0) + 1 }), {});
  return (
    <div className="view">
      <header className="view-head"><div><h1>Knowledge library</h1><p>Only approved documents ground answers. Drafts, pending, rejected and retired files are never retrieved.</p></div>
        </header>
      <div className="chips-row">{["approved", "pending", "draft", "rejected", "archived", "retired"].filter((s) => counts[s]).map((s) => <span key={s} className={`tag ${s}`}>{counts[s]} {s}</span>)}</div>
      <div className="toolbar"><div className="search"><Icon name="search" size={16} /><input value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && onReload()} placeholder="Search title or code…" aria-label="Search policies" /></div>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter status"><option value="">All statuses</option>{["approved", "pending", "draft", "rejected", "archived", "retired"].map((s) => <option key={s}>{s}</option>)}</select></div>
      <div className="table-card"><table><thead><tr><th>Document</th><th>Version</th><th>Sections</th><th>Status</th><th>Updated</th><th /></tr></thead>
        <tbody>{docs.map((d) => (
          <tr key={d.id}><td><b>{d.title}</b><small>{d.doc_code}</small></td><td>v{d.version}</td><td>{d.chunks}</td><td><span className={`tag ${d.status}`}>{d.status}</span></td><td>{d.updated_at ? ago(d.updated_at) : "-"}</td>
            <td className="acts">{editor && ["draft", "rejected"].includes(d.status) && <button className="btn mini" onClick={() => onSubmit(d.id)}>Submit for review</button>}
              {canDecide && d.status === "pending" && <><button className="btn mini bad" onClick={() => onDecide(d.id, "rejected")}>Reject</button><button className="btn mini ok" onClick={() => onDecide(d.id, "approved")}>Approve</button></>}
              {canDecide && d.status === "approved" && <button className="btn mini" onClick={() => onDecide(d.id, "archived")}>Archive</button>}</td></tr>))}
        </tbody></table>{!docs.length && <div className="empty small"><p>No documents match.</p></div>}</div>
    </div>
  );
}

export function SharedView({ items }) {
  return (
    <div className="view"><header className="view-head"><div><h1>Shared with me</h1><p>Approved policies your administrator granted to your account.</p></div><span className="tag ok">{items.length} documents</span></header>
      <div className="table-card"><table><thead><tr><th>Document</th><th>Version</th><th>Status</th><th>Shared</th></tr></thead>
        <tbody>{items.map((d) => <tr key={d.id}><td><b>{d.title}</b><small>{d.doc_code}</small></td><td>v{d.version}</td><td><span className="tag approved">approved</span></td><td>{d.shared_at}</td></tr>)}</tbody></table>
        {!items.length && <div className="empty small"><p>Nothing has been shared with you yet.</p></div>}</div></div>
  );
}
