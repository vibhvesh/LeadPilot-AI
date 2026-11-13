const groups = [
  { title: "WORKSPACE", items: ["Overview", "Lead Discovery", "Leads & CRM", "Pipeline & Follow-ups", "Tasks & Team"] },
  { title: "AI WORKSPACE", items: ["Agent Workspace", "AI Intelligence", "Execution History"] },
  { title: "MANAGEMENT", items: ["Reports & Analytics", "Activity & Audit"] },
  { title: "ADMINISTRATION", items: ["Users & Permissions", "Integrations & API Keys", "System Configuration"] },
];
export default function App() {
  return <div className="app">
    <header className="topbar"><div className="brand">LeadPilot AI <span>CANBERRAAI · TMS-LEAD · VERSION 2</span></div><div className="account"><b>Foundation environment</b><small>Authentication setup pending</small></div></header>
    <main className="layout"><aside className="sidebar">{groups.map(g=><section key={g.title}><h3>{g.title}</h3>{g.items.map(item=><button className={item==="Overview"?"nav active":"nav"} key={item}>{item}</button>)}</section>)}</aside>
      <section className="content"><div className="eyebrow">VERSION 2 / MILESTONE 1</div><h1>Platform foundation</h1><p className="intro">The modular LeadPilot workspace. Identity, approvals, permissions and live business modules are being built on the Version 2 foundation.</p>
        <div className="cards"><article><span>01 / IDENTITY</span><h2>Google authentication</h2><p>OAuth configuration and secure sessions are the next implementation slice.</p><em>Planned</em></article><article><span>02 / GOVERNANCE</span><h2>User approval</h2><p>New accounts remain pending until Super Admin approval.</p><em>Planned</em></article><article><span>03 / SECURITY</span><h2>Roles & permissions</h2><p>Backend-enforced access for Super Admin, Admin, Manager, Member and Viewer.</p><em>Planned</em></article></div>
        <div className="notice"><b>Development status</b><p>API scaffold, PostgreSQL and Redis service definitions, and frontend shell are included. This is not yet a production login system.</p></div>
      </section></main><footer>LeadPilot AI · CanberraAI · Version 2.0</footer></div>;
}
