import logging
from typing import Dict, Any, Optional
import json
import time
import asyncio
from livekit import api
from app.core.config import settings

logger = logging.getLogger(__name__)

class LiveKitService:
    def __init__(self):
        self.livekit_api = api.LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key, 
            api_secret=settings.livekit_api_secret
        )
        logger.info(f"LiveKit service initialisé avec URL: {settings.livekit_url}")
    
    async def create_room(self, room_name: str, empty_timeout: int = 300) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"Création de salle LiveKit: nom={room_name}, timeout={empty_timeout}s")
        
        try:
            request = api.CreateRoomRequest(
                name=room_name,
                empty_timeout=empty_timeout
            )
            
            response = await self.livekit_api.room.create_room(request)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Salle LiveKit créée avec succès: nom={response.name}, sid={response.sid}, temps={elapsed_time:.2f}s")
            
            # Log des détails complets pour le débogage
            details = {
                'name': response.name,
                'sid': response.sid,
                'empty_timeout': response.empty_timeout,
                'max_participants': response.max_participants,
                'creation_time': str(response.creation_time) if hasattr(response, 'creation_time') else None,
                'turn_password': response.turn_password if hasattr(response, 'turn_password') else None,
            }
            logger.debug(f"Détails de la salle créée: {json.dumps(details)}")
            
            return {
                "room_name": response.name,
                "room_sid": response.sid,
                "status": "created",
                "elapsed_time_ms": int(elapsed_time * 1000)
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Erreur lors de la création de la salle LiveKit: {e}, temps={elapsed_time:.2f}s")
            return {"status": "error", "error": str(e), "elapsed_time_ms": int(elapsed_time * 1000)}
    
    async def create_agent_dispatch(self, agent_name: str, room_name: str, metadata: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"Dispatch d'agent LiveKit: agent={agent_name}, salle={room_name}, metadata={metadata}")
        
        try:
            # Préparation des options de dispatch
            dispatch_options = {
                "agent_name": agent_name,
                "room": room_name
            }
            
            # Ajout des métadonnées si fournies
            if metadata:
                dispatch_options["metadata"] = metadata
            
            # Dispatch de l'agent
            response = await self.livekit_api.agent_dispatch.create_dispatch(**dispatch_options)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Agent dispatché avec succès: agent={agent_name}, salle={room_name}, temps={elapsed_time:.2f}s")
            
            return {
                "dispatch_id": getattr(response, 'id', None),
                "agent_name": agent_name,
                "room_name": room_name,
                "status": "dispatched",
                "elapsed_time_ms": int(elapsed_time * 1000)
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Erreur lors du dispatch de l'agent: {e}, temps={elapsed_time:.2f}s")
            # Log détaillé de l'exception
            logger.exception("Détails complets de l'erreur de dispatch")
            return {
                "status": "error", 
                "error": str(e), 
                "elapsed_time_ms": int(elapsed_time * 1000)
            }
    
    async def _check_agent_status(self, agent_name: str, room_name: str) -> None:
        """
        Vérifie si l'agent a bien été dispatché dans la salle en listant les participants
        """
        try:
            # Attendre un peu que l'agent rejoigne la salle
            await asyncio.sleep(1)
            
            # Lister les participants dans la salle
            list_request = api.ListParticipantsRequest(room=room_name)
            participants = await self.livekit_api.room.list_participants(list_request)
            
            # Vérifier si l'agent est présent dans la salle
            agent_found = False
            for participant in participants:
                logger.debug(f"Participant dans la salle {room_name}: {participant.identity}, name={participant.name}")
                if participant.name == agent_name or participant.identity == agent_name:
                    agent_found = True
                    logger.info(f"Agent {agent_name} trouvé dans la salle {room_name}")
                    break
            
            if not agent_found:
                logger.warning(f"Agent {agent_name} PAS trouvé dans la salle {room_name} après dispatch")
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du statut de l'agent: {e}")

    async def list_rooms(self) -> Dict[str, Any]:
        """
        Liste toutes les salles actives sur le serveur LiveKit
        """
        try:
            response = await self.livekit_api.room.list_rooms()
            rooms = [{"name": room.name, "sid": room.sid, "num_participants": room.num_participants} 
                     for room in response]
            
            logger.info(f"Nombre de salles actives: {len(rooms)}")
            return {"status": "success", "rooms": rooms}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des salles: {e}")
            return {"status": "error", "error": str(e)}

    async def get_agent_workers(self) -> Dict[str, Any]:
        """
        Liste tous les workers d'agents disponibles
        """
        try:
            # Cette méthode peut ne pas être disponible dans toutes les versions de l'API
            # Si vous utilisez la dernière version, décommentez cette section
            """
            response = await self.livekit_api.agent.list_workers()
            workers = [{"name": worker.name, "id": worker.id, "state": worker.state} 
                      for worker in response]
            
            logger.info(f"Nombre de workers d'agents: {len(workers)}")
            return {"status": "success", "workers": workers}
            """
            
            # Pour l'instant, renvoyer une valeur factice
            return {"status": "success", "workers": []}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des workers d'agents: {e}")
            return {"status": "error", "error": str(e)}

# Instancier le service
livekit_service = LiveKitService()
