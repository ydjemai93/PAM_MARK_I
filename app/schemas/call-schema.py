from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.schemas.agent import Agent

class CallBase(BaseModel):
    """Schéma de base pour les appels"""
    agent_id: int
    phone_number: str
    direction: str
    status: str

class CallCreate(CallBase):
    """Schéma pour la création d'appels"""
    pass

class CallUpdate(BaseModel):
    """Schéma pour la mise à jour d'appels"""
    status: Optional[str] = None
    duration: Optional[int] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    end_time: Optional[datetime] = None

class CallInDB(CallBase):
    """Schéma pour les appels en base de données"""
    id: int
    call_sid: Optional[str] = None
    duration: Optional[int] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None

    class Config:
        orm_mode = True

class Call(CallInDB):
    """Schéma pour les réponses d'API"""
    agent: Optional[Agent] = None
