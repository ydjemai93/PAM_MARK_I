import logging
from typing import Dict, Any, Optional
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
    
    async def create_room(self, room_name: str, empty_timeout: int = 300) -> Dict[str, Any]:
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
            logger.error(f"Error creating room: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_agent_dispatch(self, agent_name: str, room_name: str, metadata: Optional[str] = None) -> Dict[str, Any]:
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
            logger.error(f"Error dispatching agent: {e}")
            return {"status": "error", "error": str(e)}

livekit_service = LiveKitService()
