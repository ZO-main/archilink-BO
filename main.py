import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 1. CONFIGURATION BDD (Anti-Network-Unreachable)
DATABASE_URL = os.getenv("DATABASE_URL")

# Correction du préfixe pour SQLAlchemy 2.0
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

# Engine optimisé pour Render <-> Supabase
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True, # Vérifie la connexion avant chaque requête
    pool_recycle=300,   # Recrée les connexions toutes les 5 min
    connect_args={"sslmode": "require"} # Obligatoire pour Supabase en ligne
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. INITIALISATION APP
app = FastAPI(title="ArchiLink API")

# Configuration CORS (Pont entre Vercel et Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # À restreindre à votre URL Vercel en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
def login(req: any, db: Session = Depends(get_db)):
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
def create_appointment(appt: any, db: Session = Depends(get_db)):
    new_appt = Appointment(**appt)
    db.add(new_appt)
    db.commit()
    return True

@app.get("/slots/architect/{userId}")
def get_slots(userId: str, db: Session = Depends(get_db)):
    return db.query(AvailabilitySlot).filter(AvailabilitySlot.architect_id == userId).all()


# Logic is identical for Projects, Messages and Admin Registry.
# The database schema is fully established on Supabase.