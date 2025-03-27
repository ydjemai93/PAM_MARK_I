from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any
import logging
from app.core.security import verify_token
from app.services.livekit_service import livekit_service
from app.services.sip_service import sip_service
from app.services.agent_service import agent_service  # Importer le nouveau service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/agents/deploy", response_model=Dict[str, Any])
async def deploy_agent(
    agent_data: Dict[str, Any] = Body(...),
    token_payload: Dict[str, Any] = Depends(verify_token)
):
    """Déploie un agent dans LiveKit"""
    logger.info(f"Tentative de déploiement d'agent: {agent_data}")
    
    agent_id = agent_data.get("agent_id")
    name = agent_data.get("name")
    prompt_template = agent_data.get("prompt_template")
    
    # Validation des données d'entrée
    if not agent_id:
        logger.error("Agent ID manquant dans la requête")
        raise HTTPException(status_code=400, detail="Agent ID is required")
    
    # Déployer l'agent à l'aide du service
    try:
        deploy_result = await agent_service.deploy_agent(
            agent_id=str(agent_id),
            name=name if isinstance(name, str) else str(name),
            prompt_template=prompt_template if isinstance(prompt_template, str) else str(prompt_template)
        )
        
        logger.info(f"Agent déployé avec succès: {deploy_result}")
        
        return {
            "agent_id": agent_id,
            "worker_id": deploy_result.get("worker_id"),
            "status": "deployed"
        }
    except Exception as e:
        logger.error(f"Erreur lors du déploiement de l'agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to deploy agent: {str(e)}")

@router.post("/calls/initiate", response_model=Dict[str, Any])
async def initiate_call(
    call_data: Dict[str, Any] = Body(...),
    token_payload: Dict[str, Any] = Depends(verify_token)
):
    """Initie un appel téléphonique"""
    logger.info(f"Tentative d'initiation d'appel: {call_data}")
    
    agent_id = call_data.get("agent_id")
    phone_number = call_data.get("phone_number")
    trunk_id = call_data.get("trunk_id")
    call_id = call_data.get("call_id")
    worker_id = call_data.get("worker_id")
    
    if not all([agent_id, phone_number, trunk_id, call_id, worker_id]):
        missing_fields = [field for field in ["agent_id", "phone_number", "trunk_id", "call_id", "worker_id"] 
                         if not call_data.get(field)]
        logger.error(f"Champs manquants dans la requête d'appel: {missing_fields}")
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing_fields)}")
    
    # Création de la salle
    room_name = f"call-{agent_id}-{phone_number.replace('+', '')}"
    logger.info(f"Création de la salle LiveKit: {room_name}")
    room_result = await livekit_service.create_room(room_name)
    
    if room_result.get("status") != "created":
        logger.error(f"Échec de création de la salle LiveKit: {room_result}")
        raise HTTPException(status_code=500, detail="Failed to create room")
    
    # Dispatch de l'agent
    logger.info(f"Dispatch de l'agent: worker_id={worker_id}, room={room_name}")
    dispatch_result = await livekit_service.create_agent_dispatch(worker_id, room_name)
    
    if dispatch_result.get("status") != "dispatched":
        logger.error(f"Échec du dispatch de l'agent: {dispatch_result}")
        raise HTTPException(status_code=500, detail="Failed to dispatch agent")
    
    # Initiation de l'appel
    logger.info(f"Initiation de l'appel téléphonique: trunk={trunk_id}, phone={phone_number}, room={room_name}")
    call_result = await sip_service.make_outbound_call(trunk_id, phone_number, room_name, call_id)
    
    if call_result.get("status") == "error":
        logger.error(f"Échec de l'appel téléphonique: {call_result}")
        raise HTTPException(status_code=500, detail=call_result.get("error"))
    
    logger.info(f"Appel initié avec succès: call_sid={call_result.get('participant_id')}, status={call_result.get('status')}")
    
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
    logger.info(f"Tentative de création de trunk SIP: {trunk_data}")
    
    name = trunk_data.get("name")
    phone_number = trunk_data.get("phone_number")
    auth_username = trunk_data.get("auth_username")
    auth_password = trunk_data.get("auth_password")
    
    if not all([name, phone_number, auth_username, auth_password]):
        missing_fields = [field for field in ["name", "phone_number", "auth_username", "auth_password"] 
                         if not trunk_data.get(field)]
        logger.error(f"Champs manquants dans la requête de trunk: {missing_fields}")
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing_fields)}")
    
    trunk_result = await sip_service.create_outbound_trunk(name, phone_number, auth_username, auth_password)
    
    if trunk_result.get("status") == "error":
        logger.error(f"Échec de création du trunk SIP: {trunk_result}")
        raise HTTPException(status_code=500, detail=trunk_result.get("error"))
    
    logger.info(f"Trunk SIP créé avec succès: trunk_id={trunk_result.get('trunk_id')}")
    
    return trunk_result
