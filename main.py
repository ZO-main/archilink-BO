import os
import uvicorn
from fastapi import FastAPI

app = FastAPI()

if __name__ == "__main__":
    # Render fournit la variable PORT, sinon 8000 par défaut
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)