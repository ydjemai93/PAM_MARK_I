from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

class Call(Base):
    """Modèle pour les appels téléphoniques"""
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String, unique=True, index=True, nullable=True)  # ID d'appel du fournisseur SIP
    agent_id = Column(Integer, ForeignKey("agents.id"))
    phone_number = Column(String)
    direction = Column(String)  # "inbound" ou "outbound"
    status = Column(String)  # "initiated", "in-progress", "completed", "failed"
    duration = Column(Integer, nullable=True)  # durée en secondes
    recording_url = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    agent = relationship("Agent", back_populates="calls")
