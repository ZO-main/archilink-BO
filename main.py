import os
from fastapi import fastapi, depends, httpexception
from fastapi.middleware.cors import corsmiddleware
from sqlalchemy import create_engine, column, string, integer, foreignkey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, session

# 1. configuration bdd (anti-network-unreachable)
database_url = os.getenv("database_url")

# correction du préfixe pour sqlalchemy 2.0
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)

# engine optimisé pour render <-> supabase
engine = create_engine(
    database_url,
    pool_pre_ping=true, # vérifie la connexion avant chaque requête
    pool_recycle=300,   # recrée les connexions toutes les 5 min
    connect_args={"sslmode": "require"} # obligatoire pour supabase en ligne
)

sessionlocal = sessionmaker(autocommit=false, autoflush=false, bind=engine)
base = declarative_base()

# 2. initialisation app
app = fastapi(title="archilink api")

# configuration cors (pont entre vercel et render)
app.add_middleware(
    corsmiddleware,
    allow_origins=["*"], # à restreindre à votre url vercel en prod
    allow_credentials=true,
    allow_methods=["*"],
    allow_headers=["*"],
)

# fonction pour obtenir la session bdd
def get_db():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()

# 3. vos routes (exemples à adapter selon vos fichiers)
# --- routes ---
@app.get("/")
def read_root():
    return {"status": "archilink api is live"}

@app.post("/auth/login")
def login(req: any, db: session = depends(get_db)):
    user = db.query(user).filter(user.email == req.email).first()
    if not user: raise httpexception(status_code=404, detail="user not found")
    return user

@app.get("/architects")
def get_architects(db: session = depends(get_db)):
    profiles = db.query(architectprofile).all()
    results = []
    for p in profiles:
        u = db.query(user).filter(user.id == p.user_id).first()
        if u:
            results.append({
                "userid": p.user_id, "bio": p.bio, "location": p.location,
                "rating": p.rating, "reviewcount": p.review_count,
                "pricepersession": p.price_per_session, "user": u
            })
    return results

@app.post("/appointments")
def create_appointment(appt: any, db: session = depends(get_db)):
    new_appt = appointment(**appt)
    db.add(new_appt)
    db.commit()
    return true

@app.get("/slots/architect/{userid}")
def get_slots(userid: str, db: session = depends(get_db)):
    return db.query(availabilityslot).filter(availabilityslot.architect_id == userid).all()


# logic is identical for projects, messages and admin registry.
# the database schema is fully established on supabase.