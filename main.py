import os
import uuid
import json
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal

from fastapi import FastAPI, HTTPException, status, Depends, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Date, Time, ForeignKey, Text, Numeric, JSON, or_, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import NullPool

# 1. CONFIGURATION BDD (Anti-Network-Unreachable)
DATABASE_URL = os.getenv("DATABASE_URL")

# Force le protocole correct et ajoute des sécurités de connexion
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Vérifie si la connexion est morte avant d'échouer
    pool_size=5,         # Limite le nombre de connexions pour rester en gratuit
    max_overflow=10,
    connect_args={"sslmode": "require"} # Sécurité obligatoire pour Supabase
)

# --- UTILS ---
def to_camel(string: str) -> str:
    parts = string.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])

def to_snake(string: str) -> str:
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', '_', string).lower()

# --- MODELS ---
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    firm_id = Column(String, ForeignKey("firms.id"), nullable=True)
    is_verified = Column(Boolean, default=False)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)

class Firm(Base):
    __tablename__ = "firms"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String)
    city = Column(String)
    zip_code = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ArchitectProfile(Base):
    __tablename__ = "architect_profiles"
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    matricule = Column(String, unique=True)
    bio = Column(Text)
    location = Column(String)
    specialties = Column(JSON) # List of strings
    price_per_session = Column(Integer, default=80)
    rating = Column(Float, default=4.9)
    review_count = Column(Integer, default=0)
    portfolio = Column(JSON, default=[]) # List of objects
    services = Column(JSON, default=[]) # List of objects
    address_street = Column(String)
    address_city = Column(String)
    address_zip = Column(String)
    phone_mobile = Column(String)
    phone_office = Column(String)
    practice_zip = Column(String)
    is_public = Column(Boolean, default=True)
    status = Column(String, default="PENDING")

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, default="CONCEPT")
    client_id = Column(String, ForeignKey("users.id"))
    architect_id = Column(String, ForeignKey("users.id"))
    progress = Column(Integer, default=0)
    last_update = Column(DateTime, default=datetime.utcnow)
    thumbnail = Column(String)
    address = Column(String)
    budget = Column(Numeric(15, 2))
    surface = Column(Integer)
    phases = Column(JSON, default=[])
    documents = Column(JSON, default=[])
    constraints = Column(JSON, default=[])
    comments = Column(JSON, default=[])

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(String, primary_key=True, index=True)
    client_id = Column(String, ForeignKey("users.id"))
    architect_id = Column(String, ForeignKey("users.id"))
    slot_id = Column(String, nullable=True)
    type = Column(String, nullable=False)
    date_time = Column(DateTime, nullable=False)
    status = Column(String, default="PENDING")
    price_at_booking = Column(Numeric(10, 2))
    duration_minutes = Column(Integer, default=30)
    payment_method = Column(String)
    payment_status = Column(String, default="PENDING")
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)

class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"
    id = Column(String, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=30)
    type = Column(String, nullable=False)
    architect_id = Column(String, ForeignKey("users.id"))
    is_booked = Column(Boolean, default=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, index=True)
    sender_id = Column(String, ForeignKey("users.id"))
    receiver_id = Column(String, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

class VisioSession(Base):
    __tablename__ = "visio_sessions"
    id = Column(String, primary_key=True, index=True)
    appointment_id = Column(String, ForeignKey("appointments.id"))
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    status = Column(String, default="WAITING_FOR_ARCHITECT")
    architect_id = Column(String, ForeignKey("users.id"))
    client_id = Column(String, ForeignKey("users.id"))

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String, primary_key=True, index=True)
    number = Column(String, unique=True, nullable=False)
    date = Column(Date, default=date.today)
    due_date = Column(Date)
    client_id = Column(String, ForeignKey("users.id"))
    architect_id = Column(String, ForeignKey("users.id"))
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    status = Column(String, default="DRAFT")
    items = Column(JSON, default=[])
    notes = Column(Text)
    tax_exempt = Column(Boolean, default=False)

class UserFeedback(Base):
    __tablename__ = "user_feedbacks"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default="OPEN")
    priority = Column(String, default="NORMAL")
    created_at = Column(DateTime, default=datetime.utcnow)

class OfficialArchitect(Base):
    __tablename__ = "official_registry"
    id = Column(String, primary_key=True, index=True)
    matricule = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    region = Column(String)
    is_active = Column(Boolean, default=True)

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(String, primary_key=True, index=True)
    firm_id = Column(String, ForeignKey("firms.id"))
    author_id = Column(String, ForeignKey("users.id"))
    title = Column(String)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# --- APP ---
app = FastAPI(title="ArchiLink API v3.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- AUTH ---
class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None

@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# --- USERS ---
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.get("/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users")
def create_user(data: Dict = Body(...), db: Session = Depends(get_db)):
    user_id = data.get("id") or str(uuid.uuid4())
    new_user = User(
        id=user_id,
        name=data.get("name"),
        email=data.get("email").lower(),
        role=data.get("role"),
        avatar=data.get("avatar"),
        firm_id=data.get("firm_id")
    )
    db.add(new_user)
    db.commit()
    return True

@app.put("/users/{user_id}")
def update_user(user_id: str, data: Dict = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(404)
    for k, v in data.items():
        if hasattr(user, k): setattr(user, k, v)
    db.commit()
    return True

@app.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return True

@app.get("/users/firm/{firm_id}")
def get_firm_collaborators(firm_id: str, db: Session = Depends(get_db)):
    return db.query(User).filter(User.firm_id == firm_id).all()

# --- ARCHITECTS ---
@app.get("/architects")
def get_all_architects(db: Session = Depends(get_db)):
    # Join profile with user
    results = db.query(ArchitectProfile, User).join(User, ArchitectProfile.user_id == User.id).all()
    out = []
    for profile, user in results:
        p_dict = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
        u_dict = {c.name: getattr(user, c.name) for c in user.__table__.columns}
        p_dict["user"] = u_dict
        out.append(p_dict)
    return out

@app.get("/architects/{user_id}")
def get_architect_profile(user_id: str, db: Session = Depends(get_db)):
    profile = db.query(ArchitectProfile).filter(ArchitectProfile.user_id == user_id).first()
    if not profile:
        # Create empty profile if user is architect but has no profile record
        user = db.query(User).filter(User.id == user_id).first()
        if user and ("ARCHITECT" in user.role or "DIR_CABINET" in user.role or "COLLABORATOR" in user.role):
            profile = ArchitectProfile(user_id=user_id, specialties=[])
            db.add(profile)
            db.commit()
            db.refresh(profile)
        else:
            raise HTTPException(404, "Profile not found")
    return profile

@app.put("/architects/{user_id}")
def update_architect_profile(user_id: str, data: Dict = Body(...), db: Session = Depends(get_db)):
    profile = db.query(ArchitectProfile).filter(ArchitectProfile.user_id == user_id).first()
    if not profile:
        profile = ArchitectProfile(user_id=user_id)
        db.add(profile)
    
    prof_data = data.get("profile", {})
    for k, v in prof_data.items():
        if hasattr(profile, k): setattr(profile, k, v)
    
    avatar = data.get("avatar")
    if avatar:
        user = db.query(User).filter(User.id == user_id).first()
        if user: user.avatar = avatar
        
    db.commit()
    return True

# --- SLOTS ---
@app.get("/slots/architect/{user_id}")
def get_architect_slots(user_id: str, db: Session = Depends(get_db)):
    return db.query(AvailabilitySlot).filter(AvailabilitySlot.architect_id == user_id).all()

@app.post("/slots")
def create_slot(data: Dict = Body(...), db: Session = Depends(get_db)):
    slot = AvailabilitySlot(
        id=data.get("id") or str(uuid.uuid4()),
        date=datetime.strptime(data.get("date"), "%Y-%m-%d").date(),
        start_time=datetime.strptime(data.get("start_time"), "%H:%M").time(),
        duration_minutes=data.get("duration_minutes", 30),
        type=data.get("type"),
        architect_id=data.get("architect_id")
    )
    db.add(slot)
    db.commit()
    return True

@app.delete("/slots/{slot_id}")
def delete_slot(slot_id: str, db: Session = Depends(get_db)):
    slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.id == slot_id).first()
    if slot:
        db.delete(slot)
        db.commit()
    return True

# --- APPOINTMENTS ---
@app.get("/appointments/user/{user_id}")
def get_user_appointments(user_id: str, is_pro: bool = False, db: Session = Depends(get_db)):
    if is_pro:
        return db.query(Appointment).filter(Appointment.architect_id == user_id).all()
    return db.query(Appointment).filter(Appointment.client_id == user_id).all()

@app.get("/appointments/{appt_id}")
def get_appointment(appt_id: str, db: Session = Depends(get_db)):
    return db.query(Appointment).filter(Appointment.id == appt_id).first()

@app.post("/appointments")
def create_appointment(data: Dict = Body(...), db: Session = Depends(get_db)):
    appt_id = data.get("id") or str(uuid.uuid4())
    dt_str = data.get("date_time")
    # Handle ISO formats
    if "Z" in dt_str: dt_str = dt_str.replace("Z", "")
    dt = datetime.fromisoformat(dt_str)

    new_appt = Appointment(
        id=appt_id,
        client_id=data.get("client_id"),
        architect_id=data.get("architect_id"),
        slot_id=data.get("slot_id"),
        type=data.get("type"),
        date_time=dt,
        status=data.get("status", "CONFIRMED"),
        price_at_booking=data.get("price_at_booking"),
        duration_minutes=data.get("duration_minutes", 30),
        payment_method=data.get("payment_method"),
        payment_status=data.get("payment_status", "PENDING"),
        project_id=data.get("project_id")
    )
    db.add(new_appt)
    
    # Mark slot as booked
    slot_id = data.get("slot_id")
    if slot_id:
        slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.id == slot_id).first()
        if slot: slot.is_booked = True
        
    db.commit()
    return True

# --- PROJECTS ---
@app.get("/projects/user/{user_id}")
def get_user_projects(user_id: str, db: Session = Depends(get_db)):
    return db.query(Project).filter(or_(Project.client_id == user_id, Project.architect_id == user_id)).all()

@app.post("/projects")
def create_project(data: Dict = Body(...), db: Session = Depends(get_db)):
    new_proj = Project(
        id=data.get("id") or str(uuid.uuid4()),
        title=data.get("title"),
        status=data.get("status", "CONCEPT"),
        client_id=data.get("client_id"),
        architect_id=data.get("architect_id"),
        progress=data.get("progress", 0),
        thumbnail=data.get("thumbnail"),
        address=data.get("address"),
        budget=data.get("budget"),
        surface=data.get("surface"),
        phases=data.get("phases", []),
        documents=data.get("documents", []),
        constraints=data.get("constraints", []),
        comments=data.get("comments", [])
    )
    db.add(new_proj)
    db.commit()
    return True

@app.delete("/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if proj:
        db.delete(proj)
        db.commit()
    return True

# --- MESSAGES ---
@app.get("/messages/conversation")
def get_conversation(u1: str, u2: str, db: Session = Depends(get_db)):
    return db.query(Message).filter(
        or_(
            and_(Message.sender_id == u1, Message.receiver_id == u2),
            and_(Message.sender_id == u2, Message.receiver_id == u1)
        )
    ).order_by(Message.timestamp.asc()).all()

@app.post("/messages")
def post_message(data: Dict = Body(...), db: Session = Depends(get_db)):
    msg = Message(
        id=str(uuid.uuid4()),
        sender_id=data.get("sender_id"),
        receiver_id=data.get("receiver_id"),
        content=data.get("content")
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

# --- VISIO ---
@app.get("/visio/appointment/{appt_id}")
def get_visio_session(appt_id: str, db: Session = Depends(get_db)):
    return db.query(VisioSession).filter(VisioSession.appointment_id == appt_id).first()

@app.post("/visio/start")
def start_visio(data: Dict = Body(...), db: Session = Depends(get_db)):
    appt_id = data.get("appointment_id")
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt: raise HTTPException(404)
    
    # Clean existing
    db.query(VisioSession).filter(VisioSession.appointment_id == appt_id).delete()
    
    now = datetime.utcnow()
    duration = data.get("duration", 30)
    
    sess = VisioSession(
        id=str(uuid.uuid4()),
        appointment_id=appt_id,
        started_at=now,
        expires_at=now + timedelta(minutes=duration),
        status="OPEN",
        architect_id=appt.architect_id,
        client_id=appt.client_id
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess

@app.post("/visio/appointment/{appt_id}/close")
def close_visio(appt_id: str, db: Session = Depends(get_db)):
    sess = db.query(VisioSession).filter(VisioSession.appointment_id == appt_id).first()
    if sess:
        sess.status = "FINISHED"
        db.commit()
    return True

# --- INVOICES ---
@app.get("/invoices/user/{user_id}")
def get_user_invoices(user_id: str, db: Session = Depends(get_db)):
    return db.query(Invoice).filter(or_(Invoice.client_id == user_id, Invoice.architect_id == user_id)).all()

@app.post("/invoices")
def create_invoice(data: Dict = Body(...), db: Session = Depends(get_db)):
    inv = Invoice(
        id=data.get("id") or str(uuid.uuid4()),
        number=data.get("number"),
        date=datetime.strptime(data.get("date"), "%Y-%m-%d").date() if data.get("date") else date.today(),
        due_date=datetime.strptime(data.get("due_date"), "%Y-%m-%d").date() if data.get("due_date") else None,
        client_id=data.get("client_id"),
        architect_id=data.get("architect_id"),
        project_id=data.get("project_id"),
        status=data.get("status", "DRAFT"),
        items=data.get("items", []),
        notes=data.get("notes"),
        tax_exempt=data.get("tax_exempt", False)
    )
    db.add(inv)
    db.commit()
    return True

@app.patch("/invoices/{invoice_id}")
def patch_invoice(invoice_id: str, data: Dict = Body(...), db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv: raise HTTPException(404)
    for k, v in data.items():
        if hasattr(inv, k): setattr(inv, k, v)
    db.commit()
    return True

# --- ADMIN ---
@app.get("/admin/firms")
def admin_get_firms(db: Session = Depends(get_db)):
    return db.query(Firm).all()

@app.post("/admin/firms")
def admin_create_firm(data: Dict = Body(...), db: Session = Depends(get_db)):
    firm = Firm(
        id=str(uuid.uuid4()),
        name=data.get("name"),
        address=data.get("address"),
        city=data.get("city"),
        zip_code=data.get("zip_code")
    )
    db.add(firm)
    db.commit()
    return True

@app.get("/admin/sessions")
def admin_get_sessions(db: Session = Depends(get_db)):
    return db.query(VisioSession).all()

@app.get("/admin/messages")
def admin_get_messages(db: Session = Depends(get_db)):
    return db.query(Message).all()

@app.get("/admin/feedback")
def admin_get_feedbacks(db: Session = Depends(get_db)):
    return db.query(UserFeedback).all()

@app.patch("/admin/feedback/{fb_id}/status")
def admin_update_feedback(fb_id: str, data: Dict = Body(...), db: Session = Depends(get_db)):
    fb = db.query(UserFeedback).filter(UserFeedback.id == fb_id).first()
    if fb:
        fb.status = data.get("status")
        db.commit()
    return True

@app.get("/admin/registry")
def admin_get_registry(db: Session = Depends(get_db)):
    return db.query(OfficialArchitect).all()

@app.post("/admin/registry/bulk")
def admin_bulk_registry(data: List[Dict] = Body(...), db: Session = Depends(get_db)):
    # Simple strategy: clear and refill for demo or merge
    for item in data:
        matricule = item.get("matricule")
        existing = db.query(OfficialArchitect).filter(OfficialArchitect.matricule == matricule).first()
        if existing:
            existing.full_name = item.get("full_name")
            existing.region = item.get("region")
        else:
            db.add(OfficialArchitect(
                id=str(uuid.uuid4()),
                matricule=matricule,
                full_name=item.get("full_name"),
                region=item.get("region")
            ))
    db.commit()
    return True

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
