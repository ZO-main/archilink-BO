import os
import uvicorn
from fastapi import FastAPI

app = FastAPI()

if __name__ == "__main__":
    # Render fournit la variable PORT, sinon 8000 par défaut
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
	
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# --- CONFIGURATION DU BRIDGE CORS ---

# Liste des origines autorisées
origins = [
    "http://localhost:3000",          # Pour vos tests en local (React)
    "https://archilink.vercel.app/",   # REMPLACEZ par votre URL Vercel réelle
    "*"                               # Utilisez "*" uniquement pour tester si ça bloque
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Autorise les sites dans la liste
    allow_credentials=True,
    allow_methods=["*"],              # Autorise GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],              # Autorise tous les headers (Content-Type, Authorization...)
)

# --- VOS ROUTES CI-DESSOUS ---
@app.get("/")
def read_root():
    return {"message": "API ArchiLink opérationnelle"}