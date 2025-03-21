from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.base import get_db
from app.models.agent import Agent
from app.schemas.agent import Agent as AgentSchema, AgentCreate, AgentUpdate
from app.core.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=AgentSchema, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crée un nouvel agent IA"""
    db_agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        prompt_template=agent_data.prompt_template,
        owner_id=current_user["id"]
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

@router.get("/", response_model=List[AgentSchema])
async def read_agents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Récupère tous les agents de l'utilisateur"""
    agents = db.query(Agent).filter(Agent.owner_id == current_user["id"]).offset(skip).limit(limit).all()
    return agents

@router.get("/{agent_id}", response_model=AgentSchema)
async def read_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Récupère un agent spécifique"""
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == current_user["id"]).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.put("/{agent_id}", response_model=AgentSchema)
async def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Met à jour un agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == current_user["id"]).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Mettre à jour les champs
    update_data = agent_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)
        
    db.commit()
    db.refresh(agent)
    return agent

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Supprime un agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == current_user["id"]).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    db.delete(agent)
    db.commit()
