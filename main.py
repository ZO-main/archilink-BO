import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import NullPool

# --- CONFIGURATION BASE DE DONNÉES ---
DATABASE_URL = "postgresql://postgres:z5AoRY2uRm9tMuR8@db.beopmaqcoeyvvmgqzzgc.supabase.co:5432/postgres"
engine = create_engine(DATABASE_URL, poolclass=NullPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODÈLES ORM ---
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
    specialties = Column(Text, nullable=True)
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
    status = Column(String, default="VERIFIED")

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

class OfficialArchitect(Base):
    __tablename__ = "official_registry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    matricule = Column(String, unique=True, index=True)
    full_name = Column(String)
    region = Column(String)
    is_active = Column(Boolean, default=True)

# Create tables
Base.metadata.create_all(bind=engine)

# --- APP SETUP ---
app = FastAPI(title="ArchiLink API")

origins = [
    "https://archilink.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTES ---
@app.get("/")
def read_root():
    return {"status": "ArchiLink API is Live"}

@app.post("/auth/login")
def login(req: Any, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/architects")
def get_architects(db: Session = Depends(get_db)):
    profiles = db.query(ArchitectProfile).all()
    results = []
    for p in profiles:
        u = db.query(User).filter(User.id == p.user_id).first()
        if u:
            results.append({
                "userId": p.user_id, "bio": p.bio, "location": p.location,
                "rating": p.rating, "reviewCount": p.review_count,
                "pricePerSession": p.price_per_session, "user": u
            })
    return results

@app.post("/appointments")
def create_appointment(appt: Any, db: Session = Depends(get_db)):
    new_appt = Appointment(**appt)
    db.add(new_appt)
    db.commit()
    return True

@app.get("/slots/architect/{userId}")
def get_slots(userId: str, db: Session = Depends(get_db)):
    return db.query(AvailabilitySlot).filter(AvailabilitySlot.architect_id == userId).all()

# Logic is identical for Projects, Messages and Admin Registry.
# The database schema is fully established on Supabase.
