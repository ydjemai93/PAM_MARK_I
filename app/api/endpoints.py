from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any
import logging
from app.core.security import verify_token
from app.services.livekit_service import livekit_service
from app.services.sip_service import sip_service

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
    
    if not name:
        logger.warning(f"Nom d'agent manquant pour agent_id={agent_id}, utilisation d'un nom par défaut")
        name = f"Agent-{agent_id}"
    
    # Simulation du déploiement de l'agent dans LiveKit
    # Dans une implémentation réelle, vous appellerez un service LiveKit ici
    # Exemple : result = await livekit_service.deploy_agent(agent_id, name, prompt_template)
    
    # Pour le moment, nous simulons simplement une réponse
    worker_id = f"agent-{agent_id}"
    
    logger.info(f"Agent déployé avec succès: agent_id={agent_id}, worker_id={worker_id}")
    
    # Dans une version future, vous pourriez enregistrer des métriques
    # metrics.increment("agent.deployed")
    
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

@router.get("/agents/status", response_model=Dict[str, Any])
async def get_agents_status(
    token_payload: Dict[str, Any] = Depends(verify_token)
):
    """Récupère le statut de tous les agents déployés"""
    logger.info("Récupération du statut des agents")
    
    try:
        # Récupérer les workers d'agents
        workers_result = await livekit_service.get_agent_workers()
        
        if workers_result.get("status") != "success":
            logger.error(f"Échec de récupération des workers d'agents: {workers_result}")
            raise HTTPException(status_code=500, detail="Failed to retrieve agent workers")
        
        # Récupérer les salles actives
        rooms_result = await livekit_service.list_rooms()
        
        if rooms_result.get("status") != "success":
            logger.error(f"Échec de récupération des salles: {rooms_result}")
            raise HTTPException(status_code=500, detail="Failed to retrieve rooms")
        
        logger.info(f"Statut récupéré: {len(workers_result.get('workers', []))} workers, {len(rooms_result.get('rooms', []))} salles")
        
        return {
            "workers": workers_result.get("workers", []),
            "rooms": rooms_result.get("rooms", []),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut des agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}/status", response_model=Dict[str, Any])
async def get_agent_status(
    agent_id: str,
    token_payload: Dict[str, Any] = Depends(verify_token)
):
    """Récupère le statut d'un agent spécifique"""
    worker_id = f"agent-{agent_id}"
    logger.info(f"Récupération du statut de l'agent: {worker_id}")
    
    try:
        # Récupérer les workers d'agents
        workers_result = await livekit_service.get_agent_workers()
        
        if workers_result.get("status") != "success":
            logger.error(f"Échec de récupération des workers d'agents: {workers_result}")
            raise HTTPException(status_code=500, detail="Failed to retrieve agent workers")
        
        # Filtrer pour trouver l'agent spécifié
        agent_workers = [worker for worker in workers_result.get("workers", []) 
                        if worker.get("name") == worker_id]
        
        if not agent_workers:
            logger.warning(f"Agent non trouvé: {worker_id}")
            return {
                "agent_id": agent_id,
                "worker_id": worker_id,
                "status": "not_found",
                "active_rooms": []
            }
        
        # Récupérer les salles actives
        rooms_result = await livekit_service.list_rooms()
        
        active_rooms = []
        if rooms_result.get("status") == "success":
            # Note: Ceci est une approximation, car il est difficile de savoir quelles salles
            # sont associées à un agent spécifique sans informations supplémentaires
            # Dans une implémentation réelle, vous pourriez stocker cette relation
            for room in rooms_result.get("rooms", []):
                if f"agent-{agent_id}" in room.get("name", ""):
                    active_rooms.append(room)
        
        logger.info(f"Statut de l'agent {worker_id}: {agent_workers[0].get('state')}, salles actives: {len(active_rooms)}")
        
        return {
            "agent_id": agent_id,
            "worker_id": worker_id,
            "status": agent_workers[0].get("state", "unknown"),
            "worker_details": agent_workers[0],
            "active_rooms": active_rooms
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut de l'agent {worker_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
