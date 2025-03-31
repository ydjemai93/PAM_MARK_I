import logging
import time
from typing import Dict, Any, Optional
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
        """
        Crée une salle LiveKit ou la récupère si elle existe déjà
        """
        start_time = time.time()
        logger.info(f"Création de salle LiveKit: nom={room_name}, timeout={empty_timeout}s")
        
        try:
            # Vérifier si la salle existe déjà
            try:
                room_info = await self.livekit_api.room.get_room(api.GetRoomRequest(name=room_name))
                logger.info(f"Salle existante récupérée: {room_name}")
                
                return {
                    "room_name": room_info.name,
                    "room_sid": room_info.sid,
                    "status": "existing",
                    "elapsed_time_ms": int((time.time() - start_time) * 1000)
                }
            except Exception as e:
                # La salle n'existe pas, on continue pour la créer
                logger.debug(f"La salle {room_name} n'existe pas encore: {e}")
            
            # Créer la salle
            request = api.CreateRoomRequest(
                name=room_name,
                empty_timeout=empty_timeout
            )
            
            response = await self.livekit_api.room.create_room(request)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Salle LiveKit créée: nom={response.name}, sid={response.sid}, temps={elapsed_time:.2f}s")
            
            return {
                "room_name": response.name,
                "room_sid": response.sid,
                "status": "created",
                "elapsed_time_ms": int(elapsed_time * 1000)
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Erreur lors de la création de la salle: {e}, temps={elapsed_time:.2f}s")
            return {"status": "error", "error": str(e), "elapsed_time_ms": int(elapsed_time * 1000)}
    
    async def create_agent_dispatch(self, agent_name: str, room_name: str, metadata: Optional[str] = None) -> Dict[str, Any]:
        """
        Dispatch un agent dans une salle LiveKit
        """
        start_time = time.time()
        logger.info(f"Dispatch d'agent: agent={agent_name}, salle={room_name}, metadata={metadata}")
        
        try:
            # Définir le métadata par défaut si non fourni
            if not metadata:
                metadata = f"{{\"dispatch_time\": {int(time.time())}}}"
            
            # Créer la requête de dispatch
            request = api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata=metadata
            )
            
            # Dispatcher l'agent
            response = await self.livekit_api.agent_dispatch.create_dispatch(request)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Agent dispatché: id={response.id}, agent={agent_name}, temps={elapsed_time:.2f}s")
            
            # Vérifier asynchronement si l'agent a bien rejoint la salle
            asyncio.create_task(self._check_agent_status(agent_name, room_name))
            
            return {
                "dispatch_id": response.id,
                "agent_name": agent_name,
                "room_name": room_name,
                "status": "dispatched",
                "elapsed_time_ms": int(elapsed_time * 1000)
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Erreur lors du dispatch: {e}, temps={elapsed_time:.2f}s")
            return {
                "status": "error", 
                "error": str(e), 
                "elapsed_time_ms": int(elapsed_time * 1000)
            }
    
    async def _check_agent_status(self, agent_name: str, room_name: str) -> None:
        """
        Vérifie si l'agent a rejoint la salle avec succès
        """
        try:
            # Attendre un peu que l'agent rejoigne
            await asyncio.sleep(2)
            
            # Lister les participants
            request = api.ListParticipantsRequest(room=room_name)
            participants = await self.livekit_api.room.list_participants(request)
            
            # Vérifier si l'agent est présent
            agent_found = False
            for participant in participants:
                logger.debug(f"Participant dans {room_name}: identity={participant.identity}, name={participant.name}")
                if participant.name == agent_name or participant.identity == agent_name:
                    agent_found = True
                    logger.info(f"Agent {agent_name} trouvé dans la salle {room_name}")
                    break
            
            if not agent_found:
                logger.warning(f"Agent {agent_name} non trouvé dans la salle {room_name} après dispatch")
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'agent: {e}")

# Instancier le service
livekit_service = LiveKitService()
