from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.db.init_db import create_tables
from app.api.routes import api_router

# Configuration du logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="API pour la gestion des agents téléphoniques IA",
    version="0.1.0",
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routers API
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    """Événement de démarrage de l'application"""
    # Création des tables si elles n'existent pas
    create_tables()
    logger.info("Application started")

@app.on_event("shutdown")
async def shutdown_event():
    """Événement d'arrêt de l'application"""
    logger.info("Application shutdown")

@app.get("/")
async def root():
    """Route racine pour vérifier que l'API est en ligne"""
    return {"message": f"{settings.app_name} is running"}

@app.get("/health")
async def health_check():
    """Route de vérification de santé pour les systèmes de monitoring"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
