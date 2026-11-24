import React, { useEffect, useState } from "react";
import { adminUsers, auditLog, createAdminUser, createShare, getShares, getSettings, patchSettings, policies, revokeShare, updateAdminUser } from "./api";
import { Icon, ago } from "./ui.jsx";

const ROLE = { counsellor: "Customer", reviewer: "Reviewer", policy_manager: "Policy manager", administrator: "Administrator" };

function useFlash() {
  const [m, setM] = useState({ t: "", k: "" });
  return [m, (t, k = "ok") => { setM({ t, k }); setTimeout(() => setM({ t: "", k: "" }), 4500); }];
}
const Flash = ({ m }) => (m.t ? <div className={`banner ${m.k}`} role="status">{m.t}</div> : null);

export function UsersView({ me }) {
  const [users, setUsers] = useState([]), [busy, setBusy] = useState(false), [m, flash] = useFlash();
  const [f, setF] = useState({ username: "", display_name: "", password: "", role: "counsellor" });
  const load = async () => { const data = await adminUsers(); setUsers(data); };
  useEffect(() => { load().catch((e) => flash(e.message, "bad")); }, []);
  const create = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await createAdminUser(f); setF({ username: "", display_name: "", password: "", role: "counsellor" }); await load(); flash("Account created."); }
    catch (er) { flash(er.message, "bad"); } finally { setBusy(false); }
  };
  const toggle = async (u) => { try { await updateAdminUser(u.id, { active: !u.active }); await load(); flash(`${u.username} ${u.active ? "deactivated" : "activated"}.`); } catch (er) { flash(er.message, "bad"); } };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="view"><header className="view-head"><div><h1>User management</h1><p>Create accounts, set roles and switch access on or off. Passwords are stored as secure hashes.</p></div><span className="tag">{users.length} accounts</span></header>
      <Flash m={m} />
      <div className="grid g-form">
        <form className="card form" onSubmit={create}><h2>New account</h2>
          <label>Full name<input value={f.display_name} onChange={set("display_name")} placeholder="Jane Doe" /></label>
          <label>Username<input required minLength={3} value={f.username} onChange={set("username")} placeholder="customer.jane" autoComplete="off" /></label>
          <label>Temporary password<input required minLength={10} type="password" value={f.password} onChange={set("password")} placeholder="At least 10 characters" autoComplete="new-password" /></label>
          <label>Account type<select value={f.role} onChange={set("role")}><option value="counsellor">Customer</option><option value="reviewer">Reviewer</option><option value="policy_manager">Policy manager</option></select></label>
          <button className="btn gold" disabled={busy}>{busy ? "Creating…" : "Create account"}</button></form>
        <div className="table-card"><table><thead><tr><th>User</th><th>Role</th><th>Status</th><th /></tr></thead>
          <tbody>{users.map((u) => <tr key={u.id}><td><b>{u.display_name || u.username}</b><small>@{u.username}</small></td><td><span className="tag">{ROLE[u.role]}</span></td>
            <td><span className={`tag ${u.active ? "ok" : "bad"}`}>{u.active ? "active" : "inactive"}</span></td>
            <td className="acts"><button className="btn mini" disabled={u.id === me.id} onClick={() => toggle(u)}>{u.active ? "Deactivate" : "Activate"}</button></td></tr>)}</tbody></table></div>
      </div></div>
  );
}

export function SharingView() {
  const [docs, setDocs] = useState([]), [users, setUsers] = useState([]), [shares, setShares] = useState([]), [m, flash] = useFlash();
  const [f, setF] = useState({ document_id: "", user_id: "" });
  const load = async () => {
    const [d, u, s] = await Promise.all([policies("", "approved"), adminUsers(), getShares()]);
    setDocs(d); setUsers(u.filter((x) => x.role === "counsellor" && x.active)); setShares(s);
  };
  useEffect(() => { load().catch((e) => flash(e.message, "bad")); }, []);
  const share = async (e) => { e.preventDefault(); try { await createShare(+f.document_id, +f.user_id); setF({ document_id: "", user_id: "" }); await load(); flash("Policy shared."); } catch (er) { flash(er.message, "bad"); } };
  const revoke = async (id) => { if (!window.confirm("Revoke this customer's access?")) return; try { await revokeShare(id); await load(); flash("Access revoked."); } catch (er) { flash(er.message, "bad"); } };
  return (
    <div className="view"><header className="view-head"><div><h1>Sharing centre</h1><p>Grant a customer access to an approved policy. You can revoke at any time.</p></div><span className="tag">{shares.length} active</span></header>
      <Flash m={m} />
      <div className="grid g-form">
        <form className="card form" onSubmit={share}><h2>Share a policy</h2>
          <label>Approved document<select required value={f.document_id} onChange={(e) => setF({ ...f, document_id: e.target.value })}><option value="">Select…</option>{docs.map((d) => <option key={d.id} value={d.id}>{d.title} · v{d.version}</option>)}</select></label>
          <label>Customer<select required value={f.user_id} onChange={(e) => setF({ ...f, user_id: e.target.value })}><option value="">Select…</option>{users.map((u) => <option key={u.id} value={u.id}>{u.display_name || u.username}</option>)}</select></label>
          <button className="btn gold" disabled={!docs.length || !users.length}>Share document</button></form>
        <div className="table-card"><table><thead><tr><th>Document</th><th>Customer</th><th>Shared</th><th /></tr></thead>
          <tbody>{shares.map((s) => <tr key={s.id}><td><b>{s.document_title}</b><small>{s.doc_code} · v{s.version}</small></td><td>{s.customer_name}<small>@{s.username}</small></td><td>{s.created_at}</td>
            <td className="acts"><button className="btn mini bad" onClick={() => revoke(s.id)}>Revoke</button></td></tr>)}</tbody></table>
          {!shares.length && <div className="empty small"><p>No documents shared yet.</p></div>}</div>
      </div></div>
  );
}

export function AuditView() {
  const [rows, setRows] = useState([]), [q, setQ] = useState(""), [err, setErr] = useState("");
  useEffect(() => { const l = () => auditLog().then(setRows).catch((e) => setErr(e.message)); l(); const t = setInterval(l, 15000); return () => clearInterval(t); }, []);
  const shown = rows.filter((r) => `${r.action} ${r.actor} ${r.detail || ""}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="view"><header className="view-head"><div><h1>Audit trail</h1><p>Latest 100 consequential events. Updates every 15 seconds.</p></div></header>
      {err && <div className="banner bad">{err}</div>}
      <div className="toolbar"><div className="search"><Icon name="search" size={16} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by action, actor or detail…" aria-label="Filter audit" /></div></div>
      <ul className="card timeline">{shown.map((r, i) => <li key={i}><i /><div><b>{r.action.replaceAll("_", " ")}</b><small>{r.actor} · {r.entity || "system"}{r.entity_id ? ` #${r.entity_id}` : ""}{r.detail ? ` · ${r.detail}` : ""}</small></div><time>{ago(r.created_at)}</time></li>)}
        {!shown.length && <li className="muted pad">No events.</li>}</ul></div>
  );
}

export function SettingsView() {
  const [s, setS] = useState(null), [model, setModel] = useState(""), [m, flash] = useFlash();
  useEffect(() => { getSettings().then((x) => { setS(x); setModel(x.llm_model); }).catch((e) => flash(e.message, "bad")); }, []);
  const save = async (p) => { try { const x = await patchSettings(p); setS(x); setModel(x.llm_model); flash("Settings saved."); } catch (e) { flash(e.message, "bad"); } };
  if (!s) return <div className="view"><Flash m={m} /><p className="muted">Loading settings…</p></div>;
  return (
    <div className="view"><header className="view-head"><div><h1>Settings</h1><p>Runtime controls. API keys are never shown or stored in the browser.</p></div></header><Flash m={m} />
      <div className="grid g-two">
        <section className="card form"><h2>Language model</h2>
          <ul className="kv"><li>Provider<b>{s.llm_provider}</b></li><li>Gemini key<b>{s.gemini_configured ? "configured" : "not set"}</b></li><li>Anthropic key<b>{s.anthropic_configured ? "configured" : "not set"}</b></li><li>OpenAI key<b>{s.openai_configured ? "configured" : "not set"}</b></li></ul>
          <label>Model name<input value={model} onChange={(e) => setModel(e.target.value)} /></label>
          <button className="btn gold" onClick={() => save({ llm_model: model })}>Save model</button></section>
        <section className="card form"><h2>Governance</h2>
          <label className="switch"><input type="checkbox" checked={s.policy_manager_can_approve} onChange={(e) => save({ policy_manager_can_approve: e.target.checked })} /><span />Policy managers and reviewers may approve policies</label>
          {s.jwt_secret_is_example && <div className="banner bad"><Icon name="alert" size={15} />JWT_SECRET is still the example value. Set a long random secret before any real deployment.</div>}
        </section>
      </div></div>
  );
}
