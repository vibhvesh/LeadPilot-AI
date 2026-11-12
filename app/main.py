import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException

from fastapi.responses import HTMLResponse

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CanberraAI LeadPilot | LinkTMS</title>
<style>
:root{--bg:#f4f6fa;--ink:#172033;--muted:#68758b;--line:#e5eaf2;--blue:#3157d5;--nav:#111b32;--green:#16865b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px Inter,system-ui,Segoe UI,Arial}
.layout{display:flex;min-height:100vh}.side{width:230px;background:var(--nav);color:#fff;padding:26px 18px}.brand{font-size:20px;font-weight:750;letter-spacing:-.5px}.brand span{color:#8da8ff}.org{margin:8px 0 32px;color:#aab6ce;font-size:12px}.nav{display:block;width:100%;text-align:left;border:0;background:transparent;font:inherit;cursor:pointer;padding:12px 14px;border-radius:9px;color:#cbd4e5;margin:5px 0}.nav.active{background:#26385f;color:white}.page{display:none}.page.active{display:block}.empty{padding:28px;color:var(--muted)}.main{flex:1;padding:30px;max-width:1500px;margin:auto}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}.eyebrow{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:1px}.h{font-size:27px;font-weight:750;margin:6px 0}.sub{color:var(--muted)}.pill{background:#fff2d7;color:#8a5a00;padding:8px 12px;border-radius:20px;font-weight:650;font-size:12px}.cards{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:14px;margin:26px 0}.card,.panel{background:white;border:1px solid var(--line);border-radius:13px;padding:18px}.metric{font-size:27px;font-weight:750;margin:10px 0 3px}.muted{color:var(--muted);font-size:12px}.panel{padding:0;overflow:hidden}.panelhead{padding:18px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:10px}.panelhead h2{font-size:16px;margin:0}.btn{border:0;border-radius:8px;padding:10px 14px;background:var(--blue);color:white;font-weight:650}.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;min-width:650px}th,td{text-align:left;padding:14px 18px;border-bottom:1px solid var(--line)}th{font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.6px}td{font-size:13px}.status{background:#e9f7f0;color:var(--green);padding:5px 9px;border-radius:14px;font-size:11px;font-weight:650}.tag{color:#52617a;background:#f0f3f8;padding:5px 8px;border-radius:6px;font-size:11px}.notice{margin-top:18px;padding:14px 16px;border:1px solid #f0d69b;background:#fff9e9;border-radius:10px;color:#76520d;line-height:1.5}.footer{color:var(--muted);font-size:11px;margin-top:18px}
@media(max-width:800px){.side{width:65px;padding:20px 10px}.brand{font-size:0}.brand:first-letter{font-size:20px}.org,.nav:not(.active){display:none}.nav.active{font-size:0}.nav.active:first-letter{font-size:14px}.main{padding:20px 14px}.cards{grid-template-columns:repeat(2,minmax(120px,1fr))}}

/* Azure-inspired enterprise theme */
:root{--bg:#f3f6fb;--ink:#1b1a19;--muted:#605e5c;--line:#e1dfdd;--blue:#0078d4;--nav:#ffffff;--green:#107c10}
body{background:#f3f6fb;color:#201f1e;font-family:"Segoe UI",Inter,system-ui,Arial,sans-serif}
.layout{background:#f3f6fb}
.side{background:#fff;color:#201f1e;border-right:1px solid #e1dfdd;padding:24px 16px;box-shadow:1px 0 4px rgba(0,0,0,.035)}
.brand{color:#0078d4;font-size:21px;letter-spacing:-.6px}
.brand span{color:#323130}
.org{color:#605e5c;border-bottom:1px solid #edebe9;padding-bottom:18px;margin-bottom:20px}
.nav{color:#323130;border-radius:4px;padding:11px 12px;margin:3px 0;border-left:3px solid transparent}
.nav:hover{background:#f3f2f1;color:#0078d4}
.nav.active{background:#deecf9;color:#005a9e;border-left-color:#0078d4;font-weight:650}
.main{padding:30px 34px;max-width:1600px}
.h{font-size:28px;font-weight:600;letter-spacing:-.5px;color:#201f1e}
.eyebrow{color:#605e5c;letter-spacing:.7px}
.card,.panel{background:#fff;border:1px solid #e1dfdd;border-radius:4px;box-shadow:0 1px 2px rgba(0,0,0,.035)}
.cards{gap:16px}
.card{border-top:3px solid #0078d4;padding:17px 19px}
.metric{color:#0078d4;font-size:29px;font-weight:600}
.panel{border-radius:4px}
.panelhead{background:#fff;border-bottom:1px solid #edebe9}
.panelhead h2{font-weight:600;color:#323130}
.btn{background:#0078d4;border-radius:3px;padding:9px 15px}
.btn:hover{background:#106ebe}
th{background:#faf9f8;color:#605e5c}
td{color:#323130}
.status{background:#dff6dd;color:#107c10;border-radius:3px}
.tag{background:#f3f2f1;color:#323130;border-radius:3px}
.pill{background:#fff4ce;color:#8a6d00;border-radius:3px}
.notice{border-radius:4px}
@media(max-width:800px){.side{background:#fff}.main{padding:20px 14px}}

.settings-layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:18px;margin-top:22px}
.settings-nav{background:#fff;border:1px solid #e1dfdd;padding:8px;height:max-content}
.settings-tab{display:block;width:100%;text-align:left;border:0;background:transparent;padding:12px;color:#323130;cursor:pointer;font:inherit;border-left:3px solid transparent}
.settings-tab.active{background:#deecf9;color:#005a9e;border-left-color:#0078d4;font-weight:600}
.settings-pane{display:none}.settings-pane.active{display:block}
.setting-card{background:#fff;border:1px solid #e1dfdd;padding:20px;margin-bottom:14px}
.setting-card h3{margin:0 0 8px;font-size:16px}.setting-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.setting-field label{display:block;font-size:12px;color:#605e5c;margin-bottom:6px}
.setting-field input,.setting-field select{width:100%;padding:10px;border:1px solid #c8c6c4;border-radius:3px;font:inherit;background:#fff}
.setting-help{font-size:12px;color:#605e5c;line-height:1.5;margin-top:8px}
.pending{display:inline-block;background:#fff4ce;color:#8a6d00;padding:4px 8px;font-size:11px;margin-left:8px}
@media(max-width:800px){.settings-layout{grid-template-columns:1fr}.settings-nav{display:grid;grid-template-columns:repeat(2,1fr)}.setting-grid{grid-template-columns:1fr}}
</style></head><body><div class="layout"><aside class="side"><div class="brand">Canberra<span>AI</span></div><div class="org">LEADPILOT · LINKTMS</div><button class="nav active" data-page="overview">▦ &nbsp; Overview</button><button class="nav" data-page="leads">◎ &nbsp; Leads</button><button class="nav" data-page="followups">◷ &nbsp; Follow-ups</button><button class="nav" data-page="team">♙ &nbsp; Team</button><button class="nav" data-page="settings">⚙ &nbsp; Settings</button></aside>
<main class="main"><section id="page-overview" class="page active"><div class="top"><div><div class="eyebrow">LinkTMS workspace</div><div class="h">Lead intelligence</div><div class="sub">Recruitment sales pipeline overview</div></div><div class="pill">DEMO PREVIEW · SAMPLE DATA</div></div>
<section class="cards"><div class="card"><div class="muted">Total leads</div><div class="metric">128</div><div class="muted">Illustrative sample</div></div><div class="card"><div class="muted">New this week</div><div class="metric">24</div><div class="muted">Illustrative sample</div></div><div class="card"><div class="muted">Follow-ups due</div><div class="metric">17</div><div class="muted">Illustrative sample</div></div><div class="card"><div class="muted">Qualified</div><div class="metric">36</div><div class="muted">Illustrative sample</div></div></section>
<section class="panel"><div class="panelhead"><h2>Recent lead activity</h2><button class="btn" onclick="alert('This preview uses sample data. Sign-in and live lead actions will be enabled after secure deployment.')">＋ Add lead</button></div><div class="tablewrap"><table><thead><tr><th>Company</th><th>Signal</th><th>Region</th><th>Owner</th><th>Status</th></tr></thead><tbody>
<tr><td>Northstar Logistics</td><td><span class="tag">Hiring growth</span></td><td>United States</td><td>Unassigned</td><td><span class="status">New</span></td></tr>
<tr><td>Vertex Health Group</td><td><span class="tag">New locations</span></td><td>United States</td><td>Demo User</td><td><span class="status">Qualified</span></td></tr>
<tr><td>BluePeak Manufacturing</td><td><span class="tag">Technology expansion</span></td><td>United States</td><td>Unassigned</td><td><span class="status">New</span></td></tr>
<tr><td>Summit Retail Services</td><td><span class="tag">Hiring growth</span></td><td>United States</td><td>Demo User</td><td><span class="status">Contacted</span></td></tr>
</tbody></table></div></section>
<div class="notice"><b>Preview environment:</b> This page contains fictional sample records only. Google Workspace sign-in restricted to <b>@linktms.com</b>, individual user approval, and live database-backed dashboard actions are not enabled yet. Do not enter real customer or candidate information.</div>
<div class="footer">CanberraAI LeadPilot · Prepared for LinkTMS · Version 0.1 preview</div></section><section id="page-leads" class="page"><div class="eyebrow">LinkTMS workspace</div><div class="h">Leads</div><p class="sub">Lead pipeline workspace</p><div class="panel"><div class="panelhead"><h2>Lead records</h2></div><div class="empty">Live lead records and add/edit actions will be connected after secure sign-in and database authorization are implemented.</div></div></section><section id="page-followups" class="page"><div class="eyebrow">LinkTMS workspace</div><div class="h">Follow-ups</div><p class="sub">Keep sales conversations moving</p><div class="panel"><div class="panelhead"><h2>Follow-up queue</h2></div><div class="empty">Tasks, due dates and reminders are planned for the next development phase.</div></div></section><section id="page-team" class="page"><div class="eyebrow">LinkTMS workspace</div><div class="h">Team</div><p class="sub">Workspace members and responsibilities</p><div class="panel"><div class="panelhead"><h2>Team members</h2></div><div class="empty">Team invitations and roles will be enabled with Google Workspace authentication.</div></div></section><section id="page-settings" class="page"><div class="eyebrow">LinkTMS workspace</div><div class="h">Settings</div><p class="sub">AI providers, API integrations and workspace administration</p>
<div class="settings-layout"><nav class="settings-nav">
<button class="settings-tab active" data-setting="ai">✦ AI Configuration</button>
<button class="settings-tab" data-setting="api">⌘ API & Integrations</button>
<button class="settings-tab" data-setting="data">▤ Data & Storage</button>
<button class="settings-tab" data-setting="security">◇ Security & Access</button>
</nav><div>
<div id="setting-ai" class="settings-pane active">
<div class="setting-card"><h3>AI Provider <span class="pending">Backend pending</span></h3><div class="setting-grid">
<div class="setting-field"><label>Provider</label><select><option>OpenAI</option><option>Azure OpenAI</option><option>Self-hosted / local model</option></select></div>
<div class="setting-field"><label>Model name</label><input placeholder="e.g. gpt-4.1-mini"></div>
<div class="setting-field"><label>API endpoint</label><input placeholder="https://api.openai.com/v1"></div>
<div class="setting-field"><label>API key</label><input type="password" placeholder="Secret will be stored server-side"></div>
</div><p class="setting-help">Provider selection, model routing and encrypted secret storage require backend implementation. Never paste production API keys into this preview.</p></div>
<div class="setting-card"><h3>Model behaviour</h3><div class="setting-grid"><div class="setting-field"><label>Temperature</label><input type="number" min="0" max="2" step=".1" value=".2"></div><div class="setting-field"><label>Maximum output tokens</label><input type="number" value="2000"></div></div></div></div>
<div id="setting-api" class="settings-pane"><div class="setting-card"><h3>API Management <span class="pending">Backend pending</span></h3><div class="setting-grid"><div class="setting-field"><label>Public API base URL</label><input value="https://leads.canberravision.com/api" readonly></div><div class="setting-field"><label>Rate limit (requests/minute)</label><input type="number" value="60"></div></div><p class="setting-help">API key issuance, revocation, webhooks and integration health checks will be connected after authentication and permissions are implemented.</p></div></div>
<div id="setting-data" class="settings-pane"><div class="setting-card"><h3>Database & Storage <span class="pending">Backend pending</span></h3><div class="setting-grid"><div class="setting-field"><label>Database</label><input value="PostgreSQL 16" readonly></div><div class="setting-field"><label>Backup frequency</label><select><option>Daily</option><option>Every 6 hours</option><option>Weekly</option></select></div><div class="setting-field"><label>Data retention (days)</label><input type="number" value="365"></div><div class="setting-field"><label>Storage mode</label><select><option>VPS local volume</option><option>Object storage</option></select></div></div><p class="setting-help">Backup scheduling, restore operations and retention enforcement are not wired yet.</p></div></div>
<div id="setting-security" class="settings-pane"><div class="setting-card"><h3>Identity & Access <span class="pending">Backend pending</span></h3><div class="setting-grid"><div class="setting-field"><label>Identity provider</label><select><option>Google Workspace</option></select></div><div class="setting-field"><label>Allowed email domain</label><input value="@linktms.com" readonly></div><div class="setting-field"><label>Default role</label><select><option>Sales representative</option><option>Manager</option><option>Administrator</option></select></div><div class="setting-field"><label>New user approval</label><select><option>Admin approval required</option><option>Automatic (not recommended)</option></select></div></div><p class="setting-help">Google sign-in, domain verification, user approval, role enforcement and audit logs still need implementation.</p></div></div>
</div></div></section><script>document.querySelectorAll(".settings-tab[data-setting]").forEach(function(button){button.addEventListener("click",function(){document.querySelectorAll(".settings-tab").forEach(function(b){b.classList.remove("active")});document.querySelectorAll(".settings-pane").forEach(function(p){p.classList.remove("active")});button.classList.add("active");document.getElementById("setting-"+button.dataset.setting).classList.add("active")})});document.querySelectorAll(".nav[data-page]").forEach(function(button){button.addEventListener("click",function(){document.querySelectorAll(".nav").forEach(function(b){b.classList.remove("active")});document.querySelectorAll(".page").forEach(function(p){p.classList.remove("active")});button.classList.add("active");document.getElementById("page-"+button.dataset.page).classList.add("active")})});</script></main></div></body></html>"""

from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, ForeignKey, DateTime, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(250))
    country: Mapped[str] = mapped_column(String(80), default="USA")
    signal_type: Mapped[str] = mapped_column(String(80), default="hiring")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="new")
    owner: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    author: Mapped[str] = mapped_column(String(320))
    content: Mapped[str] = mapped_column(Text)

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    decision: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text, default="")

Base.metadata.create_all(engine)
app = FastAPI(
    title="CanberraAI Lead Generation System for TMS LLC",
    version="0.1.0",
    description="Recruitment sales lead intelligence and team collaboration"
)


@app.get("/", response_class=HTMLResponse)
def dashboard_preview():
    return DASHBOARD_HTML

def db_session():
    with SessionLocal() as db:
        yield db

def require_admin(x_admin_key: Optional[str] = Header(default=None)):
    expected = os.environ.get("ADMIN_API_KEY", "")
    if not expected or x_admin_key != expected:
        raise HTTPException(403, "Admin key required")

# Temporary development gate. Replace with authenticated user RBAC before production.
@app.get("/health")
def health(db: Session = Depends(db_session)):
    db.execute(select(1))
    return {"status": "ok", "product": "CanberraAI Lead Generation System", "customer": "TMS LLC"}

class LeadIn(BaseModel):
    company: str = Field(min_length=2, max_length=250)
    country: str = "USA"
    signal_type: str = "hiring"
    source_url: str = ""
    evidence: str = ""

class LeadPatch(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None

class NoteIn(BaseModel):
    author: str
    content: str = Field(min_length=1)

class FeedbackIn(BaseModel):
    decision: str = Field(pattern="^(accept|reject|incorrect|duplicate)$")
    reason: str = ""

@app.get("/api/leads", dependencies=[Depends(require_admin)])
def list_leads(db: Session = Depends(db_session)):
    return db.scalars(select(Lead).order_by(Lead.id.desc())).all()

@app.post("/api/leads", dependencies=[Depends(require_admin)])
def add_lead(body: LeadIn, db: Session = Depends(db_session)):
    lead = Lead(**body.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

@app.patch("/api/leads/{lead_id}", dependencies=[Depends(require_admin)])
def update_lead(lead_id: int, body: LeadPatch, db: Session = Depends(db_session)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(lead, key, value)
    db.commit()
    db.refresh(lead)
    return lead

@app.post("/api/leads/{lead_id}/notes", dependencies=[Depends(require_admin)])
def add_note(lead_id: int, body: NoteIn, db: Session = Depends(db_session)):
    if not db.get(Lead, lead_id):
        raise HTTPException(404, "Lead not found")
    note = Note(lead_id=lead_id, **body.model_dump())
    db.add(note)
    db.commit()
    return {"id": note.id}

@app.post("/api/leads/{lead_id}/feedback", dependencies=[Depends(require_admin)])
def add_feedback(lead_id: int, body: FeedbackIn, db: Session = Depends(db_session)):
    if not db.get(Lead, lead_id):
        raise HTTPException(404, "Lead not found")
    feedback = Feedback(lead_id=lead_id, **body.model_dump())
    db.add(feedback)
    db.commit()
    return {"id": feedback.id}

@app.get("/api/admin/overview", dependencies=[Depends(require_admin)])
def overview(db: Session = Depends(db_session)):
    return {
        "leads": db.scalar(select(func.count()).select_from(Lead)),
        "notes": db.scalar(select(func.count()).select_from(Note)),
        "feedback": db.scalar(select(func.count()).select_from(Feedback))
    }
