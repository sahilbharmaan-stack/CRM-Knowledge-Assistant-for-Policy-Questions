import React, { useCallback, useEffect, useRef, useState } from "react";
import { ask, escalateAnswer, decidePolicy, getSession, history, policies, reviewAnswer, sendFeedback, setSession, sharedPolicies, submitPolicy } from "./api";
import Analytics from "./Analytics.jsx";
import Login from "./Login.jsx";
import { AskView, HistoryView, KnowledgeView, ReviewView, SharedView } from "./Workspace.jsx";
import { AuditView, SettingsView, SharingView, UsersView } from "./Admin.jsx";
import { Icon, SandwichThemeToggle, useLive } from "./ui.jsx";

const STAFF = ["administrator", "policy_manager", "reviewer"];
const ROLE_LABEL = { administrator: "Administrator", policy_manager: "Policy manager", reviewer: "Reviewer", counsellor: "Customer" };
const THEME_KEY = "crm_theme";

function getTheme() {
  try { return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light"; } catch { return "light"; }
}

function speakWelcome(session) {
  if (typeof window === "undefined" || !window.speechSynthesis || !session) return;
  const username = session.username || "there";
  window.speechSynthesis.cancel();
  const message = new SpeechSynthesisUtterance(`Welcome ${username}, how may I help you my dear?`);
  message.lang = "en-IN";
  message.rate = 0.96;
  message.pitch = 1;
  window.speechSynthesis.speak(message);
}

export default function App() {
  const [session, setSessionState] = useState(() => getSession());
  const [theme, setTheme] = useState(getTheme);
  const [welcomeOnLogin, setWelcomeOnLogin] = useState(false);
  useEffect(() => { try { localStorage.setItem(THEME_KEY, theme); } catch {} }, [theme]);
  const handleSession = (nextSession) => { setSessionState(nextSession); setWelcomeOnLogin(true); };
  const handleLogout = () => {
    window.speechSynthesis?.cancel();
    setSession(null);
    setSessionState(null);
    setWelcomeOnLogin(false);
    try {
      localStorage.removeItem("crm_ask_cache");
      sessionStorage.removeItem("crm_session_questions");
    } catch {}
  };
  if (!session) return <Login onSession={handleSession} theme={theme} onThemeChange={setTheme} />;
  return <Shell session={session} theme={theme} playWelcome={welcomeOnLogin} onThemeChange={setTheme} onLogout={handleLogout} />;
}

function Shell({ session, theme, playWelcome, onThemeChange, onLogout }) {
  useEffect(() => { if (playWelcome) speakWelcome(session); }, [playWelcome, session]);
  const role = session.role, isAdmin = role === "administrator", isStaff = STAFF.includes(role);
  const [view, setView] = useState(() => (location.hash.slice(1) || "analytics"));
  const [menu, setMenu] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState(""), [notice, setNotice] = useState("");
  const [local, setLocal] = useState({});            // optimistic overrides keyed by answer_id
  const [fresh, setFresh] = useState([]);            // answers created in this session, newest first
  const [docs, setDocs] = useState([]), [search, setSearch] = useState(""), [pstatus, setPstatus] = useState("");
  const [shared, setShared] = useState([]);

  const handleShellLogout = () => {
    window.speechSynthesis?.cancel();
    setFresh([]);
    setLocal({});
    try {
      localStorage.removeItem("crm_ask_cache");
      sessionStorage.removeItem("crm_session_questions");
    } catch {}
    onLogout();
  };

  const go = (v) => { setView(v); setMenu(false); history_replace(v); };
  const live = useLive(() => history(), 10000, []);
  const items = (() => {
    const server = (live.data || []).filter((r) => r.answer_id).map((r) => ({ ...r, citations: r.citations || [], ...(local[r.answer_id] || {}) }));
    const ids = new Set(server.map((r) => r.answer_id));
    return [...fresh.filter((r) => !ids.has(r.answer_id)).map((r) => ({ ...r, ...(local[r.answer_id] || {}) })), ...server];
  })();
  const pending = items.filter((i) => i.review_status === "pending_review");

  const docsRequest = useRef(0);
  const loadDocs = useCallback(async () => {
    const requestId = ++docsRequest.current;
    try {
      const result = await policies(search, pstatus);
      if (requestId === docsRequest.current) setDocs(result);
    } catch (e) {
      if (requestId === docsRequest.current) setError(e.message);
    }
  }, [search, pstatus]);
  useEffect(() => {
    if (view !== "knowledge") return undefined;
    const timer = setTimeout(() => loadDocs(), 200);
    return () => { clearTimeout(timer); docsRequest.current += 1; };
  }, [view, loadDocs]);
  useEffect(() => { if (view === "shared" && role === "counsellor") sharedPolicies().then(setShared).catch((e) => setError(e.message)); }, [view, role]);

  const patch = (id, p) => setLocal((o) => ({ ...o, [id]: { ...(o[id] || {}), ...p } }));
  const onAsk = async (text) => {
    setAsking(true); setError("");
    try {
      const r = await ask(text);
      setFresh((f) => [{ query_id: r.query_id, answer_id: r.answer_id, query_text: text, topic: r.topic, topic_confidence: r.topic_confidence, query_status: r.status, answer_text: r.answer,
        citations: r.citations || [], passages: r.passages || [], provider: r.provider, model: r.model, latency_ms: r.latency_ms, review_status: r.review_status, message: r.message, created_at: new Date().toISOString().replace("T", " ").slice(0, 19) }, ...f]);
      live.refresh();
      return true;
    } catch (e) { setError(e.message); return false; } finally { setAsking(false); }
  };
  const onReview = async (id, decision) => {
    const reason = decision === "rejected" ? window.prompt("Reason for rejecting this answer:") : "";
    if (decision === "rejected" && !reason?.trim()) return;
    try { await reviewAnswer(id, decision, reason || ""); patch(id, { review_status: decision }); live.refresh(); } catch (e) { setError(e.message); }
  };
  const onFeedback = async (id, feedback) => { try { await sendFeedback(id, feedback, ""); patch(id, { feedback }); } catch (e) { setError(e.message); } };
  const onEscalate = async (id) => { try { await escalateAnswer(id); patch(id, { escalated: true }); setNotice("Escalated to a reviewer."); } catch (e) { setError(e.message); } };
  const onSubmit = async (id) => { try { await submitPolicy(id); await loadDocs(); setNotice("Submitted for approval."); } catch (e) { setError(e.message); } };
  const onDecide = async (id, decision) => {
    const reason = window.prompt(`Reason for ${decision === "approved" ? "approving" : decision === "rejected" ? "rejecting" : "archiving"} this policy:`);
    if (!reason?.trim()) return;
    try { await decidePolicy(id, decision, reason); await loadDocs(); setNotice(`Policy ${decision}.`); } catch (e) { setError(e.message); }
  };
  useEffect(() => { if (!notice) return; const t = setTimeout(() => setNotice(""), 5000); return () => clearTimeout(t); }, [notice]);

  const nav = [
    ["Insights", [["analytics", "pulse", "Analytics"]]],
    ["Work", [["ask", "chat", "Ask a question"], ["history", "clock", "History"], ...(isStaff ? [["review", "check", "Review queue", pending.length]] : [])]],
    ["Library", [["knowledge", "book", "Knowledge library"], ...(role === "counsellor" ? [["shared", "share", "Shared with me", shared.length]] : [])]],
    ...(isAdmin ? [["Administration", [["users", "users", "Users"], ["sharing", "share", "Sharing"], ["audit", "log", "Audit trail"], ["settings", "cog", "Settings"]]]] : []),
  ];
  const titles = Object.fromEntries(nav.flatMap(([, l]) => l.map(([id, , t]) => [id, t])));

  return (
    <div className={`shell ${menu ? "menu-open" : ""}`} data-theme={theme}>
      <aside className="side">
        <div className="brand"><span className="logo"><img src="/crm-logo.png" alt="" /></span><div><b>My Company</b><small>Policy intelligence</small></div></div>
        <nav aria-label="Primary">
          {nav.map(([group, links]) => (
            <div key={group} className="nav-group"><span>{group}</span>
              {links.map(([id, icon, label, count]) => (
                <button key={id} className={view === id ? "nav on" : "nav"} aria-current={view === id ? "page" : undefined} onClick={() => go(id)}>
                  <Icon name={icon} size={17} />{label}{count > 0 && <em>{count}</em>}</button>))}
            </div>))}
        </nav>
        <div className="me"><span className="avatar">{(session.display_name || session.username).slice(0, 1).toUpperCase()}</span>
          <div><b>{session.display_name || session.username}</b><small>{ROLE_LABEL[role]}</small></div>
          <button className="icon-btn" onClick={handleShellLogout} title="Sign out" aria-label="Sign out"><Icon name="out" size={17} /></button></div>
      </aside>
      {menu && <button className="scrim" aria-label="Close menu" onClick={() => setMenu(false)} />}
      <div className="main">
        <header className="topbar">
          <button className="icon-btn burger" onClick={() => setMenu(true)} aria-label="Open menu"><Icon name="menu" /></button>
          <span className="crumb">{ROLE_LABEL[role]}<i>/</i><b>{titles[view] || "Analytics"}</b></span>
          <span className="top-date">{new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}</span>
          <button className="btn mini welcome-voice" onClick={() => speakWelcome(session)} title="Play welcome message"><Icon name="volume" size={15} />Welcome voice</button>
          <SandwichThemeToggle theme={theme} onThemeChange={onThemeChange} />
        </header>
        <main className="content" id="main">
          {notice && <div className="banner ok" role="status">{notice}<button className="link" onClick={() => setNotice("")}>Dismiss</button></div>}
          {error && view !== "ask" && <div className="banner bad" role="alert">{error}<button className="link" onClick={() => setError("")}>Dismiss</button></div>}
          {view === "analytics" && <Analytics role={role} onNavigate={go} />}
          {view === "ask" && <AskView items={fresh} role={role} loading={asking} error={error} onAsk={onAsk} onReview={onReview} onFeedback={onFeedback} onEscalate={onEscalate} />}
          {view === "history" && <HistoryView items={items} role={role} onFeedback={onFeedback} onEscalate={onEscalate} onReview={onReview} />}
          {view === "review" && isStaff && <ReviewView items={pending} onReview={onReview} />}
          {view === "knowledge" && <KnowledgeView docs={docs} role={role} search={search} setSearch={setSearch} status={pstatus} setStatus={setPstatus} onReload={loadDocs} onSubmit={onSubmit} onDecide={onDecide} canDecide={isAdmin || isStaff} />}
          {view === "shared" && role === "counsellor" && <SharedView items={shared} />}
          {view === "users" && isAdmin && <UsersView me={session} />}
          {view === "sharing" && isAdmin && <SharingView />}
          {view === "audit" && isAdmin && <AuditView />}
          {view === "settings" && isAdmin && <SettingsView />}
        </main>
      </div>
    </div>
  );
}

function history_replace(v) { try { window.history.replaceState(null, "", `#${v}`); } catch {} }
