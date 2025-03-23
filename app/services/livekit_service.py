import os
import logging
from typing import Dict, List, Optional, Any

from livekit import api

from app.core.config import settings

logger = logging.getLogger(__name__)

class LiveKitService:
    """Service pour gérer les interactions avec LiveKit"""
    
    def __init__(self):
        """Initialise le service LiveKit avec les credentials de configuration"""
        self.livekit_api = api.LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key, 
            api_secret=settings.livekit_api_secret
        )
    
    async def create_agent_dispatch(self, agent_name: str, room_name: str, metadata: Optional[str] = None) -> Dict[str, Any]:
        """Dispatch un agent vers une salle LiveKit"""
        try:
            request = api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata=metadata
            )
            
            response = await self.livekit_api.agent_dispatch.create_dispatch(request)
            
            return {
                "dispatch_id": response.id,
                "agent_name": response.agent_name,
                "room_name": response.room_name,
                "status": "dispatched"
            }
        except Exception as e:
            logger.error(f"Erreur lors du dispatch de l'agent: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def create_room(self, room_name: str, empty_timeout: int = 300) -> Dict[str, Any]:
        """Crée une salle LiveKit"""
        try:
            request = api.CreateRoomRequest(
                name=room_name,
                empty_timeout=empty_timeout
            )
            
            response = await self.livekit_api.room.create_room(request)
            
            return {
                "room_name": response.name,
                "room_sid": response.sid,
                "status": "created"
            }
        except Exception as e:
            logger.error(f"Erreur lors de la création de la salle: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def list_rooms(self) -> List[Dict[str, Any]]:
        """Liste les salles LiveKit actives"""
        try:
            request = api.ListRoomsRequest()
            
            response = await self.livekit_api.room.list_rooms(request)
            
            rooms = []
            for room in response.rooms:
                rooms.append({
                    "name": room.name,
                    "sid": room.sid,
                    "num_participants": room.num_participants,
                    "active_recording": room.active_recording
                })
                
            return rooms
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des salles: {e}")
            return []

# Initialiser le service pour l'utiliser dans l'application
livekit_service = LiveKitService()
