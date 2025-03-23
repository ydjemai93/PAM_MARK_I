from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any
from app.core.security import verify_token
from app.services.livekit_service import livekit_service
from app.services.sip_service import sip_service

router = APIRouter()

@router.post("/agents/deploy", response_model=Dict[str, Any])
async def deploy_agent(
    agent_data: Dict[str, Any] = Body(...),
    token_payload: Dict[str, Any] = Depends(verify_token)
):
    """Déploie un agent dans LiveKit"""
    agent_id = agent_data.get("agent_id")
    worker_id = f"agent-{agent_id}"  # Dans un cas réel, vous déploieriez l'agent
    
    return {
        "agent_id": agent_id,
        "worker_id": worker_id,
        "status": "deployed"
    }

@router.post("/calls/initiate", response_model=Dict[str, Any])
async def initiate_call(
    call_data: Dict[str, Any] = Body(...),
    token_payload: Dict[str, Any] = Depends(verify_token)
):
    """Initie un appel téléphonique"""
    agent_id = call_data.get("agent_id")
    phone_number = call_data.get("phone_number")
    trunk_id = call_data.get("trunk_id")
    call_id = call_data.get("call_id")
    worker_id = call_data.get("worker_id")
    
    if not all([agent_id, phone_number, trunk_id, call_id, worker_id]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Création de la salle
    room_name = f"call-{agent_id}-{phone_number.replace('+', '')}"
    room_result = await livekit_service.create_room(room_name)
    
    if room_result.get("status") != "created":
        raise HTTPException(status_code=500, detail="Failed to create room")
    
    # Dispatch de l'agent
    dispatch_result = await livekit_service.create_agent_dispatch(worker_id, room_name)
    
    if dispatch_result.get("status") != "dispatched":
        raise HTTPException(status_code=500, detail="Failed to dispatch agent")
    
    # Initiation de l'appel
    call_result = await sip_service.make_outbound_call(trunk_id, phone_number, room_name, call_id)
    
    if call_result.get("status") == "error":
        raise HTTPException(status_code=500, detail=call_result.get("error"))
    
    return {
        "call_sid": call_result.get("participant_id"),
        "room_name": room_name,
        "status": call_result.get("status")
    }

@router.post("/trunks/create", response_model=Dict[str, Any])
async def create_trunk(
    trunk_data: Dict[str, Any] = Body(...),
    token_payload: Dict[str, Any] = Depends(verify_token)
):
    """Crée un trunk SIP dans LiveKit"""
    name = trunk_data.get("name")
    phone_number = trunk_data.get("phone_number")
    auth_username = trunk_data.get("auth_username")
    auth_password = trunk_data.get("auth_password")
    
    if not all([name, phone_number, auth_username, auth_password]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    trunk_result = await sip_service.create_outbound_trunk(name, phone_number, auth_username, auth_password)
    
    if trunk_result.get("status") == "error":
        raise HTTPException(status_code=500, detail=trunk_result.get("error"))
    
    return trunk_result
