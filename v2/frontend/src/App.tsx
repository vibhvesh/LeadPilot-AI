import { useEffect, useState } from "react";

type CurrentUser = { id: string; email: string; name?: string; is_super_admin: boolean; roles: string[] };
const groups = [
  { title: "WORKSPACE", items: ["Overview", "Lead Discovery", "Leads & CRM", "Pipeline & Follow-ups", "Tasks & Team"] },
  { title: "AI WORKSPACE", items: ["Agent Workspace", "AI Intelligence", "Execution History"] },
  { title: "MANAGEMENT", items: ["Reports & Analytics", "Activity & Audit"] },
  { title: "ADMINISTRATION", items: ["Users & Permissions", "Integrations & API Keys", "System Configuration"] },
];
export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("auth") === "pending") setPending(true);
    if (params.get("auth") === "error" || params.get("auth") === "unverified") setError("Google sign-in could not be completed. Please try again.");
    window.history.replaceState({}, "", window.location.pathname);
    fetch("/api/v1/auth/me", { credentials: "include" })
      .then(async r => { if (r.ok) setUser(await r.json()); })
      .catch(() => setError("Could not reach the LeadPilot API."))
      .finally(() => setLoading(false));
  }, []);
  const logout = async () => {
    await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" });
    setUser(null);
  };
  if (loading) return <div className="login-wrap"><div className="login-card"><h1>LeadPilot AI</h1><p>Connecting to your workspace…</p></div></div>;
  if (pending) return <div className="login-wrap"><div className="login-card"><div className="eyebrow">ACCESS REQUEST RECEIVED</div><h1>Approval pending</h1><p>Your Google account has been registered. The Super Admin must approve your access before you can enter LeadPilot AI.</p><a className="login-button secondary" href="/">Back to sign in</a></div></div>;
  if (!user) return <div className="login-wrap"><div className="login-card"><div className="brand dark">LeadPilot AI <span>CANBERRAAI · TMS-LEAD · VERSION 2</span></div><h1>Welcome back</h1><p>Sign in with your authorised Google account to access the LeadPilot workspace.</p>{error && <div className="error">{error}</div>}<a className="login-button" href="/api/v1/auth/google/login">Continue with Google</a><small>New users must be approved by the Super Admin.</small></div></div>;
  return <div className="app">
    <header className="topbar"><div className="brand">LeadPilot AI <span>CANBERRAAI · TMS-LEAD · VERSION 2</span></div><div className="account"><b>{user.name || user.email}</b><small>{user.is_super_admin ? "Super Admin" : user.roles.join(", ") || "Member"}</small><button className="logout" onClick={logout}>Sign out</button></div></header>
    <main className="layout"><aside className="sidebar">{groups.map(g=><section key={g.title}><h3>{g.title}</h3>{g.items.map(item=><button className={item==="Overview"?"nav active":"nav"} key={item}>{item}</button>)}</section>)}</aside>
      <section className="content"><div className="eyebrow">VERSION 2 / MILESTONE 1</div><h1>Platform foundation</h1><p className="intro">Welcome, {user.name || user.email}. Your authenticated LeadPilot workspace is connected.</p>
        <div className="cards"><article><span>01 / IDENTITY</span><h2>Google authentication</h2><p>Your Google identity is verified and your application session is active.</p><em className="good">Connected</em></article><article><span>02 / GOVERNANCE</span><h2>User approval</h2><p>New accounts remain pending until Super Admin approval.</p><em className="good">Enabled</em></article><article><span>03 / SECURITY</span><h2>Roles & permissions</h2><p>Role and data-scope enforcement is being completed in this milestone.</p><em>In progress</em></article></div>
        {user.is_super_admin && <div className="notice"><b>Super Admin access</b><p>Your account is the configured Super Admin. The next UI increment will expose pending-user approvals and role administration.</p></div>}
      </section></main><footer>LeadPilot AI · CanberraAI · Version 2.0</footer></div>;
}
