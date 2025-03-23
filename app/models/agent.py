from sqlalchemy import Boolean, Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

class Agent(Base):
    """Modèle pour les agents IA"""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    prompt_template = Column(Text)
    owner_id = Column(String, index=True)  # ID Supabase de l'utilisateur
    worker_id = Column(String, nullable=True)  # ID du worker sur LiveKit
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    calls = relationship("Call", back_populates="agent")
