import { useState, useEffect, useRef } from "react";

const API = "http://localhost:8000/api";

const api = {
  headers: () => ({
    "Content-Type": "application/json",
    ...(localStorage.getItem("token") ? { Authorization: `Bearer ${localStorage.getItem("token")}` } : {}),
  }),
  async post(path, body) {
    const r = await fetch(API + path, { method: "POST", headers: this.headers(), body: JSON.stringify(body) });
    if (!r.ok) throw await r.json();
    return r.json();
  },
  async get(path) {
    const r = await fetch(API + path, { headers: this.headers() });
    if (!r.ok) throw await r.json();
    return r.json();
  },
  async delete(path) {
    const r = await fetch(API + path, { method: "DELETE", headers: this.headers() });
    if (!r.ok) throw await r.json();
    return r.json();
  },
};

const ROLE_CONFIG = {
  admin:   { color: "#a78bfa", bg: "rgba(167,139,250,0.15)", label: "Admin",   canUpload: true,  canDelete: true  },
  hr:      { color: "#34d399", bg: "rgba(52,211,153,0.15)",  label: "HR",      canUpload: true,  canDelete: false },
  finance: { color: "#fbbf24", bg: "rgba(251,191,36,0.15)",  label: "Finance", canUpload: true,  canDelete: false },
  general: { color: "#94a3b8", bg: "rgba(148,163,184,0.15)", label: "General", canUpload: false, canDelete: false },
};

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700&family=DM+Sans:wght@300;400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0a0a0f;
    --bg2: #111118;
    --bg3: #1a1a24;
    --bg4: #22222f;
    --border: rgba(255,255,255,0.07);
    --border2: rgba(255,255,255,0.12);
    --text: #f1f0ff;
    --text2: #9896b8;
    --text3: #5c5a7a;
    --accent: #7c6ff7;
    --accent2: #a78bfa;
    --success: #34d399;
    --warning: #fbbf24;
    --danger: #f87171;
    --radius: 12px;
    --radius-sm: 8px;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: var(--bg2); }
  ::-webkit-scrollbar-thumb { background: var(--bg4); border-radius: 4px; }

  /* Animations */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  @keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position:  200% center; }
  }

  .fade-up { animation: fadeUp 0.4s ease both; }
  .fade-up-1 { animation: fadeUp 0.4s 0.05s ease both; }
  .fade-up-2 { animation: fadeUp 0.4s 0.1s ease both; }
  .fade-up-3 { animation: fadeUp 0.4s 0.15s ease both; }

  /* Login */
  .login-bg {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
    position: relative;
    overflow: hidden;
  }
  .login-bg::before {
    content: '';
    position: absolute;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(124,111,247,0.12) 0%, transparent 70%);
    top: -100px; left: 50%;
    transform: translateX(-50%);
    pointer-events: none;
  }
  .login-card {
    background: var(--bg2);
    border: 1px solid var(--border2);
    border-radius: 20px;
    padding: 48px;
    width: 420px;
    animation: fadeUp 0.5s ease;
    position: relative;
    z-index: 1;
  }
  .login-logo {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.5px;
    margin-bottom: 6px;
  }
  .login-logo span { color: var(--accent2); }
  .login-sub {
    font-size: 13px;
    color: var(--text3);
    margin-bottom: 36px;
    letter-spacing: 0.02em;
  }

  /* Inputs */
  .inp {
    width: 100%;
    padding: 12px 16px;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    margin-bottom: 12px;
  }
  .inp:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(124,111,247,0.15);
  }
  .inp::placeholder { color: var(--text3); }
  select.inp { cursor: pointer; }

  /* Buttons */
  .btn-primary {
    width: 100%;
    padding: 13px;
    background: var(--accent);
    border: none;
    border-radius: var(--radius-sm);
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    transition: background 0.2s, transform 0.1s, box-shadow 0.2s;
    margin-top: 8px;
    letter-spacing: 0.02em;
  }
  .btn-primary:hover { background: var(--accent2); box-shadow: 0 4px 20px rgba(124,111,247,0.3); }
  .btn-primary:active { transform: scale(0.98); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

  .btn-ghost {
    padding: 7px 14px;
    background: transparent;
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    color: var(--text2);
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    transition: all 0.2s;
  }
  .btn-ghost:hover { border-color: var(--accent); color: var(--accent2); }

  .btn-danger {
    padding: 6px 12px;
    background: rgba(248,113,113,0.1);
    border: 1px solid rgba(248,113,113,0.2);
    border-radius: 6px;
    color: var(--danger);
    font-size: 12px;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    transition: all 0.2s;
  }
  .btn-danger:hover { background: rgba(248,113,113,0.2); }

  /* Error / Success alerts */
  .alert-error {
    background: rgba(248,113,113,0.1);
    border: 1px solid rgba(248,113,113,0.2);
    border-radius: var(--radius-sm);
    color: var(--danger);
    padding: 10px 14px;
    font-size: 13px;
    margin-bottom: 16px;
  }
  .alert-success {
    background: rgba(52,211,153,0.1);
    border: 1px solid rgba(52,211,153,0.2);
    border-radius: var(--radius-sm);
    color: var(--success);
    padding: 10px 14px;
    font-size: 13px;
    margin-bottom: 16px;
  }

  /* Layout */
  .app-layout { display: flex; min-height: 100vh; }

  /* Sidebar */
  .sidebar {
    width: 240px;
    background: var(--bg2);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    position: fixed;
    top: 0; left: 0; bottom: 0;
    z-index: 10;
  }
  .sidebar-logo {
    padding: 28px 24px 20px;
    font-family: 'Syne', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: var(--text);
    border-bottom: 1px solid var(--border);
    letter-spacing: -0.3px;
  }
  .sidebar-logo span { color: var(--accent2); }

  .sidebar-user {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
  }
  .sidebar-username {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    margin-bottom: 4px;
  }
  .role-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  .sidebar-nav { padding: 12px 12px; flex: 1; }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    color: var(--text2);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.15s;
    margin-bottom: 2px;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
    font-family: 'DM Sans', sans-serif;
  }
  .nav-item:hover { background: var(--bg3); color: var(--text); }
  .nav-item.active { background: rgba(124,111,247,0.15); color: var(--accent2); }
  .nav-icon { font-size: 16px; width: 20px; text-align: center; }

  .sidebar-footer {
    padding: 16px 12px;
    border-top: 1px solid var(--border);
  }

  /* Main content */
  .main { margin-left: 240px; flex: 1; padding: 32px; min-height: 100vh; }

  /* Page header */
  .page-header { margin-bottom: 28px; }
  .page-title {
    font-family: 'Syne', sans-serif;
    font-size: 24px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.3px;
    margin-bottom: 4px;
  }
  .page-sub { font-size: 13px; color: var(--text3); }

  /* Cards */
  .card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    transition: border-color 0.2s;
  }
  .card:hover { border-color: var(--border2); }
  .card-title {
    font-size: 11px;
    font-weight: 500;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 16px;
  }

  /* RBAC banner */
  .rbac-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    margin-bottom: 20px;
    border: 1px solid;
  }

  /* Query page */
  .query-box {
    display: flex;
    gap: 10px;
    margin-bottom: 24px;
  }
  .query-input {
    flex: 1;
    padding: 14px 18px;
    background: var(--bg2);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 15px;
    font-family: 'DM Sans', sans-serif;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .query-input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(124,111,247,0.12);
  }
  .query-input::placeholder { color: var(--text3); }
  .btn-ask {
    padding: 14px 28px;
    background: var(--accent);
    border: none;
    border-radius: var(--radius);
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }
  .btn-ask:hover { background: var(--accent2); box-shadow: 0 4px 20px rgba(124,111,247,0.3); }
  .btn-ask:disabled { opacity: 0.5; cursor: not-allowed; }

  /* Thinking state */
  .thinking {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 20px 24px;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 16px;
  }
  .spinner {
    width: 18px; height: 18px;
    border: 2px solid var(--border2);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    flex-shrink: 0;
  }
  .thinking-text { font-size: 14px; color: var(--text2); }
  .thinking-steps { font-size: 12px; color: var(--text3); margin-top: 2px; }

  /* Answer card */
  .answer-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    margin-bottom: 16px;
    animation: fadeUp 0.3s ease;
  }
  .answer-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  .answer-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .answer-stats { display: flex; gap: 16px; align-items: center; }
  .stat-pill {
    font-size: 12px;
    color: var(--text3);
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .confidence-bar {
    width: 60px; height: 4px;
    background: var(--bg4);
    border-radius: 2px;
    overflow: hidden;
  }
  .confidence-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s ease;
  }
  .answer-text {
    font-size: 15px;
    line-height: 1.8;
    color: var(--text);
    white-space: pre-wrap;
  }
  .rewrite-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 14px;
    padding: 6px 12px;
    background: rgba(124,111,247,0.1);
    border: 1px solid rgba(124,111,247,0.2);
    border-radius: 20px;
    font-size: 12px;
    color: var(--accent2);
  }
  .reasoning-toggle {
    margin-top: 14px;
    font-size: 12px;
    color: var(--text3);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: none;
    font-family: 'DM Sans', sans-serif;
    padding: 0;
  }
  .reasoning-toggle:hover { color: var(--text2); }
  .reasoning-text {
    margin-top: 10px;
    padding: 12px;
    background: var(--bg3);
    border-radius: var(--radius-sm);
    font-size: 13px;
    color: var(--text2);
    font-style: italic;
    line-height: 1.6;
  }

  /* Sources */
  .sources-header {
    font-size: 11px;
    font-weight: 500;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 10px;
  }
  .source-item {
    padding: 12px 16px;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    margin-bottom: 6px;
    cursor: pointer;
    transition: all 0.15s;
    animation: fadeUp 0.3s ease;
  }
  .source-item:hover { border-color: var(--border2); background: var(--bg3); }
  .source-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }
  .source-name { font-size: 13px; font-weight: 500; color: var(--text); }
  .source-score {
    font-size: 11px;
    color: var(--text3);
    background: var(--bg4);
    padding: 2px 8px;
    border-radius: 10px;
  }
  .source-excerpt {
    font-size: 12px;
    color: var(--text3);
    line-height: 1.5;
    display: none;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
  }
  .source-item.expanded .source-excerpt { display: block; }
  .source-type {
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    background: var(--bg4);
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  /* Documents */
  .docs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .doc-item {
    padding: 16px 20px;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    transition: border-color 0.2s;
    animation: fadeUp 0.3s ease;
  }
  .doc-item:hover { border-color: var(--border2); }
  .doc-title { font-size: 14px; font-weight: 500; color: var(--text); margin-bottom: 4px; }
  .doc-meta { font-size: 12px; color: var(--text3); line-height: 1.6; }
  .doc-roles {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
    margin-top: 6px;
  }
  .doc-role-tag {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .status-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    margin-right: 5px;
  }
  .status-ready { background: var(--success); }
  .status-processing { background: var(--warning); animation: pulse 1s infinite; }
  .status-failed { background: var(--danger); }
  .status-pending { background: var(--text3); animation: pulse 1s infinite; }

  /* Upload form */
  .upload-area {
    border: 1px dashed var(--border2);
    border-radius: var(--radius-sm);
    padding: 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: 12px;
    position: relative;
  }
  .upload-area:hover { border-color: var(--accent); background: rgba(124,111,247,0.04); }
  .upload-area input[type=file] {
    position: absolute; inset: 0;
    opacity: 0; cursor: pointer; width: 100%; height: 100%;
  }
  .upload-icon { font-size: 28px; margin-bottom: 6px; }
  .upload-text { font-size: 13px; color: var(--text2); }
  .upload-hint { font-size: 11px; color: var(--text3); margin-top: 3px; }

  /* RBAC info box */
  .rbac-info {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 16px;
    margin-top: 16px;
  }
  .rbac-info-title {
    font-size: 11px;
    font-weight: 500;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 12px;
  }
  .rbac-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  .rbac-row:last-child { border-bottom: none; }
  .rbac-role { color: var(--text2); }
  .rbac-access { color: var(--text3); font-size: 12px; }

  /* Empty state */
  .empty-state {
    text-align: center;
    padding: 48px 24px;
    color: var(--text3);
  }
  .empty-icon { font-size: 40px; margin-bottom: 12px; opacity: 0.5; }
  .empty-text { font-size: 14px; }

  /* Divider */
  .divider {
    height: 1px;
    background: var(--border);
    margin: 20px 0;
  }

  /* Query history */
  .history-item {
    padding: 10px 14px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background 0.15s;
    border-bottom: 1px solid var(--border);
  }
  .history-item:hover { background: var(--bg3); }
  .history-q { font-size: 13px; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .history-meta { font-size: 11px; color: var(--text3); margin-top: 2px; }
`;

// ── Login ──────────────────────────────────────────────────────────────────
function LoginScreen({ onLogin }) {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!form.username || !form.password) return;
    setLoading(true); setError("");
    try {
      const fd = new FormData();
      fd.append("username", form.username);
      fd.append("password", form.password);
      const r = await fetch(API + "/auth/login", { method: "POST", body: fd });
      if (!r.ok) { setError("Invalid username or password"); setLoading(false); return; }
      const data = await r.json();
      localStorage.setItem("token", data.access_token);
      onLogin(data.user);
    } catch { setError("Connection error — is the backend running?"); }
    setLoading(false);
  };

  return (
    <div className="login-bg">
      <div className="login-card">
        <div className="login-logo">Corporate <span>Brain</span></div>
        <div className="login-sub">Enterprise Knowledge Assistant</div>
        {error && <div className="alert-error">{error}</div>}
        <input className="inp" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
          placeholder="Username" onKeyDown={e => e.key === "Enter" && handleSubmit()} />
        <input className="inp" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
          placeholder="Password" onKeyDown={e => e.key === "Enter" && handleSubmit()} />
        <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
          {loading ? "Signing in..." : "Sign In"}
        </button>
        <div style={{ marginTop: 20, padding: 14, background: "var(--bg3)", borderRadius: 8, fontSize: 12, color: "var(--text3)", lineHeight: 1.8 }}>
          <strong style={{ color: "var(--text2)" }}>Test accounts:</strong><br />
          admin / Admin@123 · hr_user / HR@123<br />
          fin_user / Finance@123 · employee / Employee@123
        </div>
      </div>
    </div>
  );
}

// ── Sidebar ────────────────────────────────────────────────────────────────
function Sidebar({ user, activeTab, setActiveTab, onLogout }) {
  const role = ROLE_CONFIG[user.role] || ROLE_CONFIG.general;
  const navItems = [
    { id: "query",     icon: "🔍", label: "Ask a Question" },
    { id: "documents", icon: "📄", label: "Documents" },
    { id: "rbac",      icon: "🔐", label: "Access Control" },
    { id: "history",   icon: "🕑", label: "Query History" },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-logo">Corp <span>Brain</span></div>
      <div className="sidebar-user">
        <div className="sidebar-username">{user.username}</div>
        <span className="role-badge" style={{ color: role.color, background: role.bg }}>
          {role.label}
        </span>
      </div>
      <nav className="sidebar-nav">
        {navItems.map(item => (
          <button key={item.id} className={`nav-item ${activeTab === item.id ? "active" : ""}`}
            onClick={() => setActiveTab(item.id)}>
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        <button className="btn-ghost" style={{ width: "100%" }} onClick={onLogout}>Sign Out</button>
      </div>
    </div>
  );
}

// ── Query Page ─────────────────────────────────────────────────────────────
function QueryPage({ user }) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedSources, setExpandedSources] = useState({});
  const [showReasoning, setShowReasoning] = useState(false);
  const role = ROLE_CONFIG[user.role] || ROLE_CONFIG.general;

  const handleQuery = async () => {
    if (!query.trim()) return;
    setLoading(true); setError(""); setResult(null); setShowReasoning(false);
    try {
      const data = await api.post("/query", { query });
      setResult(data);
    } catch (e) { setError(e.detail || "Query failed. Please try again."); }
    setLoading(false);
  };

  const confColor = c => c > 0.75 ? "var(--success)" : c > 0.5 ? "var(--warning)" : "var(--danger)";

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">Ask a Question</div>
        <div className="page-sub">Query the knowledge base using your role access: <strong style={{ color: role.color }}>{role.label}</strong></div>
      </div>

      <div className="rbac-banner" style={{ background: role.bg, borderColor: role.color + "44", color: role.color }}>
        <span>🔐</span>
        <span>You can access: <strong>{
          { admin: "All documents (Admin + HR + Finance + General)",
            hr: "HR and General documents",
            finance: "Finance and General documents",
            general: "General documents only" }[user.role]
        }</strong></span>
      </div>

      <div className="query-box">
        <input className="query-input" value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !loading && handleQuery()}
          placeholder="Ask anything about your company knowledge base..." />
        <button className="btn-ask" onClick={handleQuery} disabled={loading || !query.trim()}>
          {loading ? "..." : "Ask →"}
        </button>
      </div>

      {loading && (
        <div className="thinking">
          <div className="spinner" />
          <div>
            <div className="thinking-text">Agent is thinking...</div>
            <div className="thinking-steps">Plan → Hybrid Retrieve → Cross-encode → Verify</div>
          </div>
        </div>
      )}

      {error && <div className="alert-error">{error}</div>}

      {result && (
        <>
          <div className="answer-card">
            <div className="answer-meta">
              <span className="answer-label">Answer</span>
              <div className="answer-stats">
                <span className="stat-pill">
                  <span style={{ color: "var(--text3)" }}>Confidence</span>
                  <div className="confidence-bar">
                    <div className="confidence-fill" style={{ width: `${result.confidence * 100}%`, background: confColor(result.confidence) }} />
                  </div>
                  <span style={{ color: confColor(result.confidence), fontWeight: 500 }}>{(result.confidence * 100).toFixed(0)}%</span>
                </span>
                <span className="stat-pill">🔁 {result.iterations} iteration{result.iterations !== 1 ? "s" : ""}</span>
              </div>
            </div>

            <div className="answer-text">{result.answer}</div>

            {result.rewrite_history?.length > 0 && (
              <div className="rewrite-pill">
                ✏️ Query rewritten: "{result.rewrite_history[0]}" → improved for better results
              </div>
            )}

            {result.reasoning && (
              <>
                <button className="reasoning-toggle" onClick={() => setShowReasoning(s => !s)}>
                  {showReasoning ? "▲" : "▼"} Agent reasoning
                </button>
                {showReasoning && <div className="reasoning-text">{result.reasoning}</div>}
              </>
            )}
          </div>

          {result.sources?.length > 0 && (
            <div className="fade-up-1">
              <div className="sources-header">Sources ({result.sources.length})</div>
              {result.sources.map((s, i) => (
                <div key={s.id || i}
                  className={`source-item ${expandedSources[i] ? "expanded" : ""}`}
                  onClick={() => setExpandedSources(prev => ({ ...prev, [i]: !prev[i] }))}>
                  <div className="source-top">
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="source-name">[{i + 1}] {s.title || s.filename}</span>
                      {s.page_num && <span style={{ fontSize: 11, color: "var(--text3)" }}>p.{s.page_num}</span>}
                      <span className="source-type">{s.chunk_type || "text"}</span>
                    </div>
                    <span className="source-score">score: {s.score?.toFixed(3)}</span>
                  </div>
                  <div className="source-excerpt">{s.excerpt}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!result && !loading && (
        <div className="empty-state fade-up-1">
          <div className="empty-icon">💬</div>
          <div className="empty-text">Ask a question to search across your knowledge base</div>
        </div>
      )}
    </div>
  );
}

// ── Documents Page ─────────────────────────────────────────────────────────
function DocumentsPage({ user, docs, onRefresh }) {
  const [form, setForm] = useState({ title: "", allowed_roles: "general" });
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState("");
  const [uploading, setUploading] = useState(false);
  const role = ROLE_CONFIG[user.role] || ROLE_CONFIG.general;

  const handleUpload = async () => {
    if (!file || !form.title) { setStatus("Please fill in title and select a file"); setStatusType("error"); return; }
    setUploading(true); setStatus(""); 
    try {
      const fd = new FormData();
      fd.append("title", form.title);
      fd.append("allowed_roles", form.allowed_roles);
      fd.append("file", file);
      const r = await fetch(API + "/documents/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        body: fd
      });
      if (!r.ok) throw new Error((await r.json()).detail);
      setStatus("Uploaded! Ingestion running in background..."); setStatusType("success");
      setFile(null); setForm({ title: "", allowed_roles: "general" });
      setTimeout(onRefresh, 2000);
    } catch (e) { setStatus("Upload failed: " + e.message); setStatusType("error"); }
    setUploading(false);
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this document and all its chunks?")) return;
    try {
      await api.delete(`/documents/${id}`);
      onRefresh();
    } catch (e) { alert("Delete failed: " + (e.detail || e.message)); }
  };

  const statusColor = s => ({ ready: "var(--success)", failed: "var(--danger)", processing: "var(--warning)", pending: "var(--text3)" })[s] || "var(--text3)";

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">Documents</div>
        <div className="page-sub">{docs.length} document{docs.length !== 1 ? "s" : ""} accessible to your role</div>
      </div>

      <div className="docs-grid">
        {/* Upload panel — only for roles that can upload */}
        {role.canUpload ? (
          <div className="card fade-up-1">
            <div className="card-title">Upload Document</div>
            <input className="inp" value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="Document title" />
            <select className="inp" value={form.allowed_roles}
              onChange={e => setForm(f => ({ ...f, allowed_roles: e.target.value }))}>
              <option value="general">General — all users</option>
              <option value="hr">HR only</option>
              <option value="finance">Finance only</option>
              <option value="hr,finance">HR + Finance</option>
              <option value="admin">Admin only</option>
              {user.role === "admin" && <option value="admin,hr,finance,general">All roles</option>}
            </select>
            <div className="upload-area">
              <input type="file" accept=".pdf,.docx,.xlsx"
                onChange={e => setFile(e.target.files[0])} />
              <div className="upload-icon">📎</div>
              <div className="upload-text">{file ? file.name : "Click to choose file"}</div>
              <div className="upload-hint">PDF, DOCX, XLSX supported</div>
            </div>
            {file && <div style={{ fontSize: 12, color: "var(--success)", marginBottom: 10 }}>✓ {file.name} ({(file.size/1024).toFixed(1)} KB)</div>}
            <button className="btn-primary" onClick={handleUpload} disabled={uploading}>
              {uploading ? "Uploading..." : "Upload & Ingest"}
            </button>
            {status && <div className={`alert-${statusType === "error" ? "error" : "success"}`} style={{ marginTop: 12, marginBottom: 0 }}>{status}</div>}
          </div>
        ) : (
          <div className="card fade-up-1">
            <div className="card-title">Upload Documents</div>
            <div style={{ padding: "24px 0", textAlign: "center", color: "var(--text3)", fontSize: 14 }}>
              <div style={{ fontSize: 32, marginBottom: 10 }}>🔒</div>
              Your role (<strong style={{ color: role.color }}>{role.label}</strong>) does not have upload permissions.<br /><br />
              Contact an Admin, HR, or Finance user to upload documents.
            </div>
          </div>
        )}

        {/* Document list */}
        <div className="card fade-up-2">
          <div className="card-title">Knowledge Base ({docs.length})</div>
          {docs.length === 0 ? (
            <div className="empty-state" style={{ padding: "24px 0" }}>
              <div className="empty-icon">📭</div>
              <div className="empty-text">No documents accessible to your role</div>
            </div>
          ) : (
            docs.map(doc => (
              <div key={doc.id} className="doc-item" style={{ marginBottom: 8 }}>
                <div style={{ flex: 1 }}>
                  <div className="doc-title">{doc.title}</div>
                  <div className="doc-meta">
                    {doc.filename} · {doc.chunk_count} chunks
                  </div>
                  <div className="doc-roles">
                    {doc.allowed_roles.map(r => (
                      <span key={r} className="doc-role-tag"
                        style={{ color: ROLE_CONFIG[r]?.color || "var(--text3)", background: ROLE_CONFIG[r]?.bg || "var(--bg4)" }}>
                        {r}
                      </span>
                    ))}
                  </div>
                  <div style={{ marginTop: 6, fontSize: 12 }}>
                    <span className={`status-dot status-${doc.status}`} />
                    <span style={{ color: statusColor(doc.status) }}>{doc.status}</span>
                  </div>
                </div>
                {role.canDelete && (
                  <button className="btn-danger" onClick={() => handleDelete(doc.id)}>Delete</button>
                )}
              </div>
            ))
          )}
          <button className="btn-ghost" style={{ width: "100%", marginTop: 8 }} onClick={onRefresh}>↻ Refresh</button>
        </div>
      </div>
    </div>
  );
}

// ── RBAC Page ──────────────────────────────────────────────────────────────
function RBACPage({ user }) {
  const role = ROLE_CONFIG[user.role] || ROLE_CONFIG.general;
  const matrix = [
    { role: "admin",   access: ["Admin docs", "HR docs", "Finance docs", "General docs"], canUpload: true,  canDelete: true  },
    { role: "hr",      access: ["HR docs", "General docs"],                               canUpload: true,  canDelete: false },
    { role: "finance", access: ["Finance docs", "General docs"],                          canUpload: true,  canDelete: false },
    { role: "general", access: ["General docs only"],                                     canUpload: false, canDelete: false },
  ];

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">Access Control</div>
        <div className="page-sub">Role-Based Access Control — who can see and do what</div>
      </div>

      <div className="rbac-banner" style={{ background: role.bg, borderColor: role.color + "44", color: role.color, marginBottom: 24 }}>
        <span>👤</span>
        <span>You are logged in as <strong>{user.username}</strong> with role <strong>{role.label}</strong></span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {matrix.map(r => {
          const rc = ROLE_CONFIG[r.role];
          const isCurrentRole = r.role === user.role;
          return (
            <div key={r.role} className="card fade-up-1"
              style={{ borderColor: isCurrentRole ? rc.color + "44" : "var(--border)", background: isCurrentRole ? rc.bg : "var(--bg2)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <span className="role-badge" style={{ color: rc.color, background: rc.bg }}>
                  {rc.label} {isCurrentRole && "← You"}
                </span>
                <div style={{ display: "flex", gap: 6 }}>
                  <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 10, background: r.canUpload ? "rgba(52,211,153,0.15)" : "rgba(248,113,113,0.1)", color: r.canUpload ? "var(--success)" : "var(--danger)" }}>
                    {r.canUpload ? "✓ Upload" : "✗ Upload"}
                  </span>
                  <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 10, background: r.canDelete ? "rgba(52,211,153,0.15)" : "rgba(248,113,113,0.1)", color: r.canDelete ? "var(--success)" : "var(--danger)" }}>
                    {r.canDelete ? "✓ Delete" : "✗ Delete"}
                  </span>
                </div>
              </div>
              <div className="card-title">Document Access</div>
              {r.access.map(a => (
                <div key={a} style={{ fontSize: 13, color: "var(--text2)", padding: "5px 0", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 7 }}>
                  <span style={{ color: "var(--success)" }}>✓</span> {a}
                </div>
              ))}
            </div>
          );
        })}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-title">How RBAC Works in This System</div>
        <div style={{ fontSize: 14, color: "var(--text2)", lineHeight: 1.9 }}>
          Every document is tagged with <strong style={{ color: "var(--text)" }}>allowed_roles</strong> when uploaded.
          When you run a query, the hybrid search (Qdrant + Elasticsearch) automatically filters results
          to only return chunks from documents your role can access. A Finance user querying for HR documents
          will get zero results — the data is invisible to them at the vector level.
          <br /><br />
          The JWT token encodes your role, which is verified on every API request by the FastAPI backend.
        </div>
      </div>
    </div>
  );
}

// ── History Page ───────────────────────────────────────────────────────────
function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/query/history").then(setHistory).catch(() => setHistory([])).finally(() => setLoading(false));
  }, []);

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">Query History</div>
        <div className="page-sub">Your last 50 queries</div>
      </div>
      <div className="card">
        {loading && <div style={{ textAlign: "center", padding: 24, color: "var(--text3)" }}>Loading...</div>}
        {!loading && history.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🕑</div>
            <div className="empty-text">No query history yet</div>
          </div>
        )}
        {history.map((h, i) => (
          <div key={h.id || i} className="history-item">
            <div className="history-q">💬 {h.query}</div>
            <div className="history-meta">
              {h.rewritten_query && <span>Rewritten · </span>}
              Confidence: {h.confidence ? (h.confidence * 100).toFixed(0) + "%" : "—"} ·
              {new Date(h.created_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── App ────────────────────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState("query");
  const [docs, setDocs] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) api.get("/auth/me").then(setUser).catch(() => localStorage.removeItem("token"));
  }, []);

  const loadDocs = () => {
    if (user) api.get("/documents").then(setDocs).catch(() => {});
  };

  useEffect(() => { loadDocs(); }, [user]);

  const handleLogout = () => { localStorage.removeItem("token"); setUser(null); };

  if (!user) return (
    <>
      <style>{styles}</style>
      <LoginScreen onLogin={u => { setUser(u); }} />
    </>
  );

  return (
    <>
      <style>{styles}</style>
      <div className="app-layout">
        <Sidebar user={user} activeTab={activeTab} setActiveTab={setActiveTab} onLogout={handleLogout} />
        <main className="main">
          {activeTab === "query"     && <QueryPage user={user} />}
          {activeTab === "documents" && <DocumentsPage user={user} docs={docs} onRefresh={loadDocs} />}
          {activeTab === "rbac"      && <RBACPage user={user} />}
          {activeTab === "history"   && <HistoryPage />}
        </main>
      </div>
    </>
  );
}