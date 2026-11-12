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
.layout{display:flex;min-height:100vh}.side{width:230px;background:var(--nav);color:#fff;padding:26px 18px}.brand{font-size:20px;font-weight:750;letter-spacing:-.5px}.brand span{color:#8da8ff}.org{margin:8px 0 32px;color:#aab6ce;font-size:12px}.nav{padding:12px 14px;border-radius:9px;color:#cbd4e5;margin:5px 0}.nav.active{background:#26385f;color:white}.main{flex:1;padding:30px;max-width:1500px;margin:auto}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}.eyebrow{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:1px}.h{font-size:27px;font-weight:750;margin:6px 0}.sub{color:var(--muted)}.pill{background:#fff2d7;color:#8a5a00;padding:8px 12px;border-radius:20px;font-weight:650;font-size:12px}.cards{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:14px;margin:26px 0}.card,.panel{background:white;border:1px solid var(--line);border-radius:13px;padding:18px}.metric{font-size:27px;font-weight:750;margin:10px 0 3px}.muted{color:var(--muted);font-size:12px}.panel{padding:0;overflow:hidden}.panelhead{padding:18px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:10px}.panelhead h2{font-size:16px;margin:0}.btn{border:0;border-radius:8px;padding:10px 14px;background:var(--blue);color:white;font-weight:650}.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;min-width:650px}th,td{text-align:left;padding:14px 18px;border-bottom:1px solid var(--line)}th{font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.6px}td{font-size:13px}.status{background:#e9f7f0;color:var(--green);padding:5px 9px;border-radius:14px;font-size:11px;font-weight:650}.tag{color:#52617a;background:#f0f3f8;padding:5px 8px;border-radius:6px;font-size:11px}.notice{margin-top:18px;padding:14px 16px;border:1px solid #f0d69b;background:#fff9e9;border-radius:10px;color:#76520d;line-height:1.5}.footer{color:var(--muted);font-size:11px;margin-top:18px}
@media(max-width:800px){.side{width:65px;padding:20px 10px}.brand{font-size:0}.brand:first-letter{font-size:20px}.org,.nav:not(.active){display:none}.nav.active{font-size:0}.nav.active:first-letter{font-size:14px}.main{padding:20px 14px}.cards{grid-template-columns:repeat(2,minmax(120px,1fr))}}
</style></head><body><div class="layout"><aside class="side"><div class="brand">Canberra<span>AI</span></div><div class="org">LEADPILOT · LINKTMS</div><div class="nav active">▦ &nbsp; Overview</div><div class="nav">◎ &nbsp; Leads</div><div class="nav">◷ &nbsp; Follow-ups</div><div class="nav">♙ &nbsp; Team</div><div class="nav">⚙ &nbsp; Settings</div></aside>
<main class="main"><div class="top"><div><div class="eyebrow">LinkTMS workspace</div><div class="h">Lead intelligence</div><div class="sub">Recruitment sales pipeline overview</div></div><div class="pill">DEMO PREVIEW · SAMPLE DATA</div></div>
<section class="cards"><div class="card"><div class="muted">Total leads</div><div class="metric">128</div><div class="muted">Illustrative sample</div></div><div class="card"><div class="muted">New this week</div><div class="metric">24</div><div class="muted">Illustrative sample</div></div><div class="card"><div class="muted">Follow-ups due</div><div class="metric">17</div><div class="muted">Illustrative sample</div></div><div class="card"><div class="muted">Qualified</div><div class="metric">36</div><div class="muted">Illustrative sample</div></div></section>
<section class="panel"><div class="panelhead"><h2>Recent lead activity</h2><button class="btn" onclick="alert('This preview uses sample data. Sign-in and live lead actions will be enabled after secure deployment.')">＋ Add lead</button></div><div class="tablewrap"><table><thead><tr><th>Company</th><th>Signal</th><th>Region</th><th>Owner</th><th>Status</th></tr></thead><tbody>
<tr><td>Northstar Logistics</td><td><span class="tag">Hiring growth</span></td><td>United States</td><td>Unassigned</td><td><span class="status">New</span></td></tr>
<tr><td>Vertex Health Group</td><td><span class="tag">New locations</span></td><td>United States</td><td>Demo User</td><td><span class="status">Qualified</span></td></tr>
<tr><td>BluePeak Manufacturing</td><td><span class="tag">Technology expansion</span></td><td>United States</td><td>Unassigned</td><td><span class="status">New</span></td></tr>
<tr><td>Summit Retail Services</td><td><span class="tag">Hiring growth</span></td><td>United States</td><td>Demo User</td><td><span class="status">Contacted</span></td></tr>
</tbody></table></div></section>
<div class="notice"><b>Preview environment:</b> This page contains fictional sample records only. Google Workspace sign-in restricted to <b>@linktms.com</b>, individual user approval, and live database-backed dashboard actions are not enabled yet. Do not enter real customer or candidate information.</div>
<div class="footer">CanberraAI LeadPilot · Prepared for LinkTMS · Version 0.1 preview</div></main></div></body></html>"""

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
