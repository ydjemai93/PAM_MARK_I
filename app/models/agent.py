from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AgentBase(BaseModel):
    """Schéma de base pour les agents"""
    name: str
    description: Optional[str] = None
    prompt_template: str

class AgentCreate(AgentBase):
    """Schéma pour la création d'agents"""
    pass

class AgentUpdate(BaseModel):
    """Schéma pour la mise à jour d'agents"""
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_template: Optional[str] = None
    is_active: Optional[bool] = None

class AgentInDB(AgentBase):
    """Schéma pour les agents en base de données"""
    id: int
    owner_id: str
    worker_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class Agent(AgentInDB):
    """Schéma pour les réponses d'API"""
    pass
