const TOKEN_KEY = "crm_token";
// Empty = same origin (Vercel /api). Set VITE_API_URL to the Render backend URL for a split deploy.
const API_BASE = (import.meta.env && import.meta.env.VITE_API_URL) || "";

export const getSession = () => {
  try { return JSON.parse(localStorage.getItem(TOKEN_KEY)); } catch { return null; }
};
export const setSession = (s) => {
  try { s ? localStorage.setItem(TOKEN_KEY, JSON.stringify(s)) : localStorage.removeItem(TOKEN_KEY); } catch {}
};

async function request(path, options = {}) {
  const session = getSession();
  const callerHeaders = options.headers || {};
  let res;
  try {
    res = await fetch(`${API_BASE}/api${path}`, {
      ...options,
      headers: {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(session ? { Authorization: `Bearer ${session.token}` } : {}),
        ...callerHeaders,
      },
    });
  } catch {
    const apiAddress = API_BASE || (import.meta.env.DEV ? "http://localhost:8000" : window.location.origin);
    throw new Error(`Cannot connect to the API at ${apiAddress}. For local development, start it with: python -m uvicorn backend.main:app --reload --port 8000`);
  }
  if (res.status === 401 && session) { setSession(null); window.location.reload(); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `API request failed (${res.status})`);
  return data;
}

export const authStatus = () => request("/auth/status");
export const setupAdmin = (username, password, display_name) =>
  request("/auth/setup", { method: "POST", body: JSON.stringify({ username, password, display_name }) });
export const login = (username, password, panel = "any") =>
  request("/auth/login", { method: "POST", body: JSON.stringify({ username, password, panel }) });
export const ask = (query) => request("/ask", { method: "POST", body: JSON.stringify({ query }) });
export const history = () => request("/history");
export const sendFeedback = (id, feedback, note) =>
  request(`/answers/${id}/feedback`, { method: "POST", body: JSON.stringify({ feedback, note }) });
export const reviewAnswer = (id, decision, reason = "") =>
  request(`/answers/${id}/review`, { method: "POST", body: JSON.stringify({ decision, reason }) });

export const dashboard = () => request("/dashboard");
export const policies = (q = "", status = "") => {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  return request(`/policies${params.size ? `?${params}` : ""}`);
};
export const uploadPolicy = (file, metadata) => {
  const form = new FormData();
  form.append("file", file);
  form.append("doc_code", metadata.doc_code);
  form.append("title", metadata.title);
  form.append("version", metadata.version);
  return request("/policies/upload", { method: "POST", body: form });
};
export const submitPolicy = (id) => request(`/policies/${id}/submit`, { method: "POST" });
export const auditLog = () => request("/audit");
export const adminUsers = () => request("/users");
export const createAdminUser = (payload) => request("/users", { method: "POST", body: JSON.stringify(payload) });
export const updateAdminUser = (id, payload) => request(`/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
export const getShares = () => request("/shares");
export const createShare = (document_id, user_id) => request("/shares", { method: "POST", body: JSON.stringify({ document_id, user_id }) });
export const revokeShare = (id) => request(`/shares/${id}`, { method: "DELETE" });

export const sharedPolicies = () => request("/shared-policies");

// ---- analytics (live, aggregated from SQLite on every call)
export const analytics = (days = 14) => request(`/analytics?days=${days}`);
export const simulateTraffic = (count = 3) => request("/analytics/simulate", { method: "POST", body: JSON.stringify({ count }) });
export const getSettings = () => request("/settings");
export const patchSettings = (payload) => request("/settings", { method: "PATCH", body: JSON.stringify(payload) });
export const decidePolicy = (id, decision, reason) => request(`/policies/${id}/decision`, { method: "POST", body: JSON.stringify({ decision, reason }) });
export const escalateAnswer = (id, note = "") => request(`/answers/${id}/escalate`, { method: "POST", body: JSON.stringify({ note }) });
export const changePassword = (current_password, new_password) => request("/auth/password", { method: "POST", body: JSON.stringify({ current_password, new_password }) });
export const policyDetail = (id) => request(`/policies/${id}`);
