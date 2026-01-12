import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from fastapi import FastAPI, HTTPException, status, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    firm_id = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)

class ArchitectProfile(Base):
    __tablename__ = "architect_profiles"
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    specialties = Column(Text, nullable=True)  # Stocké en JSON string ou texte séparé
    bio = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    rating = Column(Float, default=4.5)
    review_count = Column(Integer, default=0)
    price_per_session = Column(Integer, default=80)
    address_street = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_zip = Column(String, nullable=True)
    practice_zip = Column(String, nullable=True)
    matricule = Column(String, nullable=True)
    phone_mobile = Column(String, nullable=True)
    phone_office = Column(String, nullable=True)
    is_public = Column(Boolean, default=True)
    status = Column(String, default="PENDING")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(String, primary_key=True, index=True)
    client_id = Column(String, ForeignKey("users.id"))
    architect_id = Column(String, ForeignKey("users.id"))
    type = Column(String, nullable=False)
    date_time = Column(DateTime, nullable=False)
    status = Column(String, default="CONFIRMED")
    price_at_booking = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, default=30)

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, default="CONCEPT")
    client_id = Column(String, ForeignKey("users.id"))
    architect_id = Column(String, ForeignKey("users.id"))
    progress = Column(Integer, default=0)
    last_update = Column(DateTime, default=datetime.utcnow)
    thumbnail = Column(String, nullable=True)

class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"
    id = Column(String, primary_key=True, index=True)
    architect_id = Column(String, ForeignKey("users.id"))
    date = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    duration_minutes = Column(Integer, default=30)
    type = Column(String, nullable=False)
    is_booked = Column(Boolean, default=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, index=True)
    sender_id = Column(String, ForeignKey("users.id"))
    receiver_id = Column(String, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

class Firm(Base):
    __tablename__ = "firms"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String, default="NORMAL")
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)

class OfficialArchitect(Base):
    __tablename__ = "official_registry"
    id = Column(String, primary_key=True, index=True)
    matricule = Column(String, unique=True, index=True)
    full_name = Column(String)
    region = Column(String)
    is_active = Column(Boolean, default=True)

class VisioSession(Base):
    __tablename__ = "visio_sessions"
    id = Column(String, primary_key=True, index=True)
    appointment_id = Column(String, ForeignKey("appointments.id"))
    started_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String, default="WAITING_FOR_ARCHITECT")
    architect_id = Column(String)
    client_id = Column(String)

# --- APP SETUP ---
app = FastAPI(title="ArchiLink API Backend")

# Liste des origines autorisées (sans slash à la fin !)
origins = [
    "https://archilink.vercel.app",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Autorise tous les verbes (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Autorise tous les headers
)


# Logic is identical for Projects, Messages and Admin Registry.
# The database schema is fully established on Supabase.
# --- DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- SCHEMAS (Pydantic) ---
class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    avatar: Optional[str] = None

# --- ROUTES ---

@app.get("/")
def health_check():
    return {"status": "online", "version": "2.1.0", "service": "ArchiLink-Core"}

# --- AUTH & USERS ---
@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user

@app.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.get("/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404)
    return user

@app.post("/users")
def create_user(user_data: Dict[str, Any], db: Session = Depends(get_db)):
    new_user = User(**user_data)
    db.add(new_user)
    db.commit()
    return True

@app.put("/users/{user_id}")
def update_user(user_id: str, data: Dict[str, Any], db: Session = Depends(get_db)):
    db.query(User).filter(User.id == user_id).update(data)
    db.commit()
    return True

@app.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    return True

@app.get("/users/firm/{firm_id}")
def get_firm_collabs(firm_id: str, db: Session = Depends(get_db)):
    return db.query(User).filter(User.firm_id == firm_id).all()

# --- ARCHITECTS ---
@app.get("/architects")
def list_architects(db: Session = Depends(get_db)):
    profiles = db.query(ArchitectProfile).all()
    results = []
    for p in profiles:
        user = db.query(User).filter(User.id == p.user_id).first()
        if user:
            # Conversion specialties string to list si besoin
            specs = p.specialties.split(',') if p.specialties else []
            p_dict = {c.name: getattr(p, c.name) for c in p.__table__.columns}
            p_dict["user"] = user
            p_dict["specialties"] = specs
            results.append(p_dict)
    return results

@app.get("/architects/{user_id}")
def get_architect_profile(user_id: str, db: Session = Depends(get_db)):
    p = db.query(ArchitectProfile).filter(ArchitectProfile.user_id == user_id).first()
    if not p: return None
    p_dict = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    p_dict["specialties"] = p.specialties.split(',') if p.specialties else []
    return p_dict

@app.put("/architects/{user_id}")
def update_architect_profile(user_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    profile_data = payload.get("profile", {})
    avatar = payload.get("avatar")
    
    # Update User Avatar if provided
    if avatar:
        db.query(User).filter(User.id == user_id).update({"avatar": avatar})
    
    # Handle Specialties list to string
    if "specialties" in profile_data and isinstance(profile_data["specialties"], list):
        profile_data["specialties"] = ",".join(profile_data["specialties"])
        
    existing = db.query(ArchitectProfile).filter(ArchitectProfile.user_id == user_id).first()
    if existing:
        for key, value in profile_data.items():
            setattr(existing, key, value)
    else:
        new_p = ArchitectProfile(user_id=user_id, **profile_data)
        db.add(new_p)
    
    db.commit()
    return True

# --- APPOINTMENTS ---
@app.get("/appointments/{appt_id}")
def get_appt(appt_id: str, db: Session = Depends(get_db)):
    return db.query(Appointment).filter(Appointment.id == appt_id).first()

@app.get("/appointments/user/{user_id}")
def get_user_appts(user_id: str, is_pro: bool = False, db: Session = Depends(get_db)):
    if is_pro:
        return db.query(Appointment).filter(Appointment.architect_id == user_id).all()
    return db.query(Appointment).filter(Appointment.client_id == user_id).all()

@app.post("/appointments")
def create_appt(data: Dict[str, Any], db: Session = Depends(get_db)):
    new_appt = Appointment(**data)
    db.add(new_appt)
    
    # Marquer le créneau comme réservé si possible
    date_iso = new_appt.date_time.date().isoformat()
    time_str = new_appt.date_time.strftime("%H:%M")
    db.query(AvailabilitySlot).filter(
        AvailabilitySlot.architect_id == new_appt.architect_id,
        AvailabilitySlot.date == date_iso,
        AvailabilitySlot.start_time == time_str
    ).update({"is_booked": True})
    
    db.commit()
    return True

# --- SLOTS (AGENDA) ---
@app.get("/slots/architect/{user_id}")
def get_arch_slots(user_id: str, db: Session = Depends(get_db)):
    return db.query(AvailabilitySlot).filter(AvailabilitySlot.architect_id == user_id).all()

@app.post("/slots")
def create_slot(data: Dict[str, Any], db: Session = Depends(get_db)):
    new_slot = AvailabilitySlot(**data)
    db.add(new_slot)
    db.commit()
    return True

@app.delete("/slots/{slot_id}")
def delete_slot(slot_id: str, db: Session = Depends(get_db)):
    db.query(AvailabilitySlot).filter(AvailabilitySlot.id == slot_id).delete()
    db.commit()
    return True

# --- PROJECTS ---
@app.get("/projects/user/{user_id}")
def get_user_projects(user_id: str, db: Session = Depends(get_db)):
    return db.query(Project).filter((Project.client_id == user_id) | (Project.architect_id == user_id)).all()

@app.post("/projects")
def create_project(data: Dict[str, Any], db: Session = Depends(get_db)):
    new_p = Project(**data)
    db.add(new_p)
    db.commit()
    return True

@app.delete("/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    db.query(Project).filter(Project.id == project_id).delete()
    db.commit()
    return True

# --- MESSAGES ---
@app.get("/messages/conversation")
def get_conv(u1: str, u2: str, db: Session = Depends(get_db)):
    return db.query(Message).filter(
        ((Message.sender_id == u1) & (Message.receiver_id == u2)) |
        ((Message.sender_id == u2) & (Message.receiver_id == u1))
    ).order_by(Message.timestamp.asc()).all()

@app.post("/messages")
def post_msg(data: Dict[str, Any], db: Session = Depends(get_db)):
    msg = Message(**data)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

# --- VISIO ---
@app.get("/visio/appointment/{appt_id}")
def get_visio(appt_id: str, db: Session = Depends(get_db)):
    return db.query(VisioSession).filter(VisioSession.appointment_id == appt_id).first()

@app.post("/visio/start")
def start_visio(payload: Dict[str, Any], db: Session = Depends(get_db)):
    appt_id = payload.get("appointmentId")
    duration = payload.get("duration", 30)
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt: raise HTTPException(status_code=404)
    
    existing = db.query(VisioSession).filter(VisioSession.appointment_id == appt_id).first()
    now = datetime.utcnow()
    expires = now + timedelta(minutes=duration)
    
    if existing:
        existing.status = "OPEN"
        existing.started_at = now
        existing.expires_at = expires
    else:
        existing = VisioSession(
            id=str(uuid.uuid4()),
            appointment_id=appt_id,
            started_at=now,
            expires_at=expires,
            status="OPEN",
            architect_id=appt.architect_id,
            client_id=appt.client_id
        )
        db.add(existing)
    
    db.commit()
    db.refresh(existing)
    return existing

@app.post("/visio/appointment/{appt_id}/close")
def close_visio(appt_id: str, db: Session = Depends(get_db)):
    db.query(VisioSession).filter(VisioSession.appointment_id == appt_id).update({"status": "FINISHED"})
    db.commit()
    return True

# --- ADMIN ---
@app.get("/admin/firms")
def list_firms(db: Session = Depends(get_db)):
    return db.query(Firm).all()

@app.post("/admin/firms")
def create_firm(data: Dict[str, Any], db: Session = Depends(get_db)):
    if "id" not in data: data["id"] = str(uuid.uuid4())
    db.add(Firm(**data))
    db.commit()
    return True

@app.get("/admin/sessions")
def list_all_sessions(db: Session = Depends(get_db)):
    return db.query(VisioSession).all()

@app.get("/admin/messages")
def list_all_msgs(db: Session = Depends(get_db)):
    return db.query(Message).order_by(Message.timestamp.desc()).limit(100).all()

@app.get("/admin/feedback")
def list_feedback(db: Session = Depends(get_db)):
    return db.query(Feedback).all()

@app.get("/admin/registry")
def list_registry(db: Session = Depends(get_db)):
    return db.query(OfficialArchitect).all()

@app.post("/admin/registry/bulk")
def bulk_registry(data: List[Dict[str, Any]], db: Session = Depends(get_db)):
    for item in data:
        if "id" not in item: item["id"] = str(uuid.uuid4())
        # Check duplicate
        exists = db.query(OfficialArchitect).filter(OfficialArchitect.matricule == item["matricule"]).first()
        if not exists:
            db.add(OfficialArchitect(**item))
    db.commit()
    return True

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
	
	
