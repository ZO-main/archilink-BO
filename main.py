import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Ajouté CORSMiddleware ici
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Any, Dict, List, Optional  # Pour corriger l'erreur 'Any' précédente


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

# 2. INITIALISATION APP
app = FastAPI()

# --- CE BLOC DOIT ÊTRE AVANT TOUTES LES ROUTES ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://archilink.vercel.app",  # Votre site Vercel
        "http://localhost:3000",         # Pour vos tests locaux
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Autorise GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # Autorise tous les headers
)


# Fonction pour obtenir la session BDD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. VOS ROUTES (Exemples à adapter selon vos fichiers)
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