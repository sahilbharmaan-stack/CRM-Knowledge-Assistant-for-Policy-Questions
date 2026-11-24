import React, { useEffect, useState } from "react";
import { authStatus, login, setSession, setupAdmin } from "./api";
import { Icon } from "./ui.jsx";

export default function Login({ onSession, theme, onThemeChange }) {
  const [f, setF] = useState({ username: "", password: "", name: "" });
  const [show, setShow] = useState(false), [setup, setSetup] = useState(false), [checking, setChecking] = useState(true);
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => { authStatus().then((r) => setSetup(!!r.needs_setup)).catch((e) => setErr(e.message)).finally(() => setChecking(false)); }, []);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try {
      const s = setup ? await setupAdmin(f.username.trim(), f.password, f.name.trim()) : await login(f.username.trim(), f.password);
      setSession(s); onSession(s);
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <main className="login" data-theme={theme}>
      <section className="login-art" aria-hidden="true">
        <div className="login-brand"><span className="logo"><img src="/crm-logo.png" alt="" /></span>My Company</div>
        <svg className="login-wave" viewBox="0 0 600 220" preserveAspectRatio="none"><path className="w1" d="M0 140 C60 80 120 190 190 120 S320 40 390 110 S520 170 600 70" /><path className="w2" d="M0 170 C80 120 140 200 220 150 S340 90 420 140 S540 190 600 120" /></svg>
        <div className="login-copy"><h1>Every answer<br />traceable to a policy.</h1><p>Grounded in approved documents, cited by version, and held for a person to approve. When the policy is silent, the assistant says so.</p>
          <ul><li><Icon name="check" size={15} />Cited by document and version</li><li><Icon name="shield" size={15} />Human review on every answer</li><li><Icon name="pulse" size={15} />Live analytics from real activity</li></ul></div>
      </section>
      <section className="login-form-wrap">
        <form className="login-form" onSubmit={submit}>
          <h2>{checking ? "Preparing…" : setup ? "Create the first administrator" : "Sign in"}</h2>
          <p className="muted">{setup ? "No administrator exists yet. This one-time step closes after the first account." : "Sign in with the credentials issued to you. Your role is detected automatically."}</p>
          {setup && <label>Your name<input required value={f.name} onChange={set("name")} autoComplete="name" /></label>}
          <label>User ID / Username<input required value={f.username} onChange={set("username")} autoComplete="username" /></label>
          <label>Password<span className="pw"><input required type={show ? "text" : "password"} minLength={setup ? 10 : undefined} value={f.password} onChange={set("password")} autoComplete={setup ? "new-password" : "current-password"} />
            <button type="button" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"}><Icon name="eye" size={17} /></button></span></label>
          {err && <div className="banner bad" role="alert">{err}</div>}
          <button className="btn gold block" disabled={busy || checking}>{busy ? "Please wait…" : setup ? "Create administrator" : "Sign in"}</button>
          <p className="fine">Internal use only. Synthetic policy data, no real learner records.</p>
        </form>
      </section>
    </main>
  );
}
