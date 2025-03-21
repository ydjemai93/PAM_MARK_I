from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/")
async def health_check(db: Session = Depends(get_db)):
    """
    Vérifie la santé de l'application.
    
    Vérifie:
    - La connexion à la base de données
    - Les variables d'environnement essentielles
    """
    # Vérifier la connexion à la base de données
    try:
        # Exécuter une requête simple
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Vérifier les variables d'environnement essentielles
    env_checks = {
        "livekit": bool(settings.livekit_url and settings.livekit_api_key and settings.livekit_api_secret),
        "openai": bool(settings.openai_api_key),
        "deepgram": bool(settings.deepgram_api_key),
        "cartesia": bool(settings.cartesia_api_key),
        "supabase": bool(settings.supabase_url and settings.supabase_key)
    }
    
    return {
        "status": "healthy",
        "database": db_status,
        "environment": env_checks
    }
