from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Création du moteur SQLAlchemy
engine = create_engine(settings.database_url)

# Création de la session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe de base pour les modèles
Base = declarative_base()

# Fonction pour obtenir une session de base de données
def get_db():
    """Fournit une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
