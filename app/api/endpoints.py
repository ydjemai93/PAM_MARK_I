from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any
import logging
from app.core.security import verify_token
from app.services.livekit_service import livekit_service
from app.services.sip_service import sip_service
from app.services.agent_service import agent_service

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
            name=name or f"agent-{agent_id}",
            prompt_template=prompt_template or ""
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
    """Initie un appel téléphonique sortant avec un agent IA"""
    logger.info(f"Initialisation d'un appel sortant: {call_data}")
    
    # Valider les données requises
    agent_id = call_data.get("agent_id")
    phone_number = call_data.get("phone_number")
    trunk_id = call_data.get("trunk_id")
    call_id = call_data.get("call_id")
    
    if not all([agent_id, phone_number, trunk_id, call_id]):
        missing_fields = [field for field in ["agent_id", "phone_number", "trunk_id", "call_id"] 
                         if not call_data.get(field)]
        logger.error(f"Champs manquants: {missing_fields}")
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing_fields)}")
    
    # Vérifier si l'agent est déjà déployé ou le déployer
    worker_id = f"agent-{agent_id}"
    agent_status = await agent_service.get_agent_status(agent_id)
    
    if agent_status.get("status") != "running":
        logger.warning(f"L'agent {agent_id} n'est pas en cours d'exécution, tentative de déploiement")
        deploy_result = await agent_service.deploy_agent(
            agent_id=str(agent_id),
            name=f"agent-{agent_id}",
            prompt_template=call_data.get("prompt_template", "")
        )
        worker_id = deploy_result.get("worker_id")
    
    # Créer une salle LiveKit pour l'appel
    room_name = f"call-{call_id}"
    logger.info(f"Création de la salle pour l'appel: {room_name}")
    
    room_result = await livekit_service.create_room(room_name)
    if room_result.get("status") not in ["created", "existing"]:
        logger.error(f"Échec de création de la salle: {room_result}")
        raise HTTPException(status_code=500, detail="Failed to create room")
    
    # Dispatcher l'agent dans la salle
    logger.info(f"Dispatching de l'agent {worker_id} dans la salle {room_name}")
    
    # Définir le metadata avec le numéro de téléphone pour que l'agent sache qui appeler
    metadata = f'{{"phone_number": "{phone_number}", "call_id": "{call_id}"}}'
    
    dispatch_result = await livekit_service.create_agent_dispatch(worker_id, room_name, metadata)
    if dispatch_result.get("status") != "dispatched":
        logger.error(f"Échec du dispatch de l'agent: {dispatch_result}")
        raise HTTPException(status_code=500, detail="Failed to dispatch agent")
    
    # Initier l'appel téléphonique
    logger.info(f"Initiation de l'appel: trunk={trunk_id}, téléphone={phone_number}")
    
    call_result = await sip_service.make_outbound_call(trunk_id, phone_number, room_name, call_id)
    if call_result.get("status") == "error":
        logger.error(f"Échec de l'appel: {call_result}")
        raise HTTPException(status_code=500, detail=call_result.get("error"))
    
    logger.info(f"Appel initié: participant_id={call_result.get('participant_id')}")
    
    return {
        "call_id": call_id,
        "participant_id": call_result.get("participant_id"),
        "room_name": room_name,
        "status": call_result.get("status"),
        "agent_id": agent_id
    }

@router.post("/trunks/create", response_model=Dict[str, Any])
async def create_trunk(
    trunk_data: Dict[str, Any] = Body(...),
    token_payload: Dict[str, Any] = Depends(verify_token)
):
    """Crée un trunk SIP dans LiveKit pour les appels sortants"""
    logger.info(f"Création d'un trunk SIP: {trunk_data}")
    
    name = trunk_data.get("name")
    phone_number = trunk_data.get("phone_number")
    auth_username = trunk_data.get("auth_username")
    auth_password = trunk_data.get("auth_password")
    
    if not all([name, phone_number, auth_username, auth_password]):
        missing_fields = [field for field in ["name", "phone_number", "auth_username", "auth_password"] 
                         if not trunk_data.get(field)]
        logger.error(f"Champs manquants: {missing_fields}")
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing_fields)}")
    
    trunk_result = await sip_service.create_outbound_trunk(name, phone_number, auth_username, auth_password)
    
    if trunk_result.get("status") == "error":
        logger.error(f"Échec de création du trunk: {trunk_result}")
        raise HTTPException(status_code=500, detail=trunk_result.get("error"))
    
    logger.info(f"Trunk créé avec succès: trunk_id={trunk_result.get('trunk_id')}")
    
    return trunk_result
