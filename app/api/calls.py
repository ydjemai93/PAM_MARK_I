from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.db.base import get_db
from app.models.agent import Agent
from app.models.call import Call
from app.services.sip_service import sip_service
from app.services.livekit_service import livekit_service
from app.core.auth import get_current_user
from app.schemas.call import CallCreate, Call as CallSchema

router = APIRouter()

@router.post("/outbound", response_model=Dict[str, Any])
async def make_outbound_call(
    phone_number: str = Body(...),
    agent_id: int = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Effectue un appel sortant en utilisant Twilio
    
    Args:
        phone_number: Numéro à appeler (format: +33xxxxxxxxx)
        agent_id: ID de l'agent à utiliser
    """
    # Récupérer l'agent
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == current_user["id"]).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Vérifier que l'agent est actif
    if not agent.is_active:
        raise HTTPException(status_code=400, detail="Agent is not active")
    
    # Créer une salle pour l'appel
    room_name = f"call-{agent.id}-{phone_number.replace('+', '')}"
    room_result = await livekit_service.create_room(room_name)
    
    if room_result.get("status") != "created":
        raise HTTPException(status_code=500, detail="Failed to create room")
    
    # Créer un enregistrement d'appel dans la base de données
    db_call = Call(
        agent_id=agent.id,
        phone_number=phone_number,
        direction="outbound",
        status="initiated"
    )
    db.add(db_call)
    db.commit()
    db.refresh(db_call)
    
    try:
        # Dispatcher l'agent dans la salle
        if agent.worker_id:
            dispatch_result = await livekit_service.create_agent_dispatch(
                agent_name=agent.worker_id,
                room_name=room_name
            )
            
            if dispatch_result.get("status") != "dispatched":
                raise HTTPException(status_code=500, detail="Failed to dispatch agent")
        
        # Effectuer l'appel via le trunk Twilio
        # Note: Dans un MVP, nous utilisons un trunk_id hardcodé pour simplifier
        # En production, vous récupéreriez le trunk_id depuis la configuration de l'utilisateur
        trunk_id = "twilio-trunk-id"  # À remplacer par votre ID de trunk réel

        call_result = await sip_service.make_outbound_call(
            trunk_id=trunk_id,
            phone_number=phone_number,
            room_name=room_name
        )
        
        if call_result.get("status") == "error":
            raise HTTPException(status_code=500, detail=call_result.get("error"))
        
        # Mettre à jour l'enregistrement d'appel
        db_call.call_sid = call_result.get("participant_id")
        db_call.status = "dialing"
        db.commit()
        
        return {
            "call_id": db_call.id,
            "status": "dialing",
            "phone_number": phone_number,
            "agent_id": agent.id,
            "room_name": room_name
        }
    
    except HTTPException as he:
        # Mettre à jour l'état de l'appel en cas d'erreur
        db_call.status = "failed"
        db.commit()
        raise he
    except Exception as e:
        # Mettre à jour l'état de l'appel en cas d'erreur
        db_call.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[CallSchema])
async def get_calls(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Récupère l'historique des appels de l'utilisateur"""
    calls = db.query(Call).join(Agent).filter(
        Agent.owner_id == current_user["id"]
    ).offset(skip).limit(limit).all()
    
    return calls

@router.get("/{call_id}", response_model=CallSchema)
async def get_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Récupère les détails d'un appel spécifique"""
    call = db.query(Call).join(Agent).filter(
        Call.id == call_id,
        Agent.owner_id == current_user["id"]
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return call
