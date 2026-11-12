import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException
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
app = FastAPI(title="LeadPilot AI", version="0.1.0")

def db_session():
    with SessionLocal() as db:
        yield db

def require_admin(x_admin_key: Optional[str] = Header(default=None)):
    expected = os.environ.get("ADMIN_API_KEY", "")
    if not expected or x_admin_key != expected:
        raise HTTPException(403, "Admin key required")

# Until OAuth and RBAC are implemented, all lead mutations require the admin key.
@app.get("/health")
def health(db: Session = Depends(db_session)):
    db.execute(select(1))
    return {"status": "ok"}

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
