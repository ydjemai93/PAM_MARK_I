import logging
from sqlalchemy.exc import SQLAlchemyError
from app.db.base import Base, engine
from app.models.agent import Agent  # Importer les modèles
from app.models.call import Call

logger = logging.getLogger(__name__)

def create_tables():
    """Crée les tables dans la base de données"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Base de données initialisée avec succès")
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
