import logging
import httpx
from typing import Dict, Any
from livekit import api
from app.core.config import settings
from app.services.livekit_service import livekit_service

logger = logging.getLogger(__name__)

class SipService:
    def __init__(self):
        self.livekit_api = api.LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key, 
            api_secret=settings.livekit_api_secret
        )
        self.xano_webhook_url = settings.xano_webhook_url
        self.xano_api_key = settings.xano_api_key
    
    async def create_outbound_trunk(self, name: str, phone_number: str, auth_username: str, auth_password: str) -> Dict[str, Any]:
        try:
            trunk = api.SIPOutboundTrunkInfo(
                name=name,
                address="sip.twilio.com",
                numbers=[phone_number],
                auth_username=auth_username,
                auth_password=auth_password
            )
            
            request = api.CreateSIPOutboundTrunkRequest(trunk=trunk)
            response = await self.livekit_api.sip.create_sip_outbound_trunk(request)
            
            return {
                "trunk_id": response.id,
                "name": response.name,
                "numbers": response.numbers,
                "status": "created"
            }
        except Exception as e:
            logger.error(f"Error creating outbound trunk: {e}")
            return {"status": "error", "error": str(e)}
    
    async def make_outbound_call(self, trunk_id: str, phone_number: str, room_name: str, call_id: str) -> Dict[str, Any]:
        try:
            request = api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_dial_to=phone_number,
                room_name=room_name,
                participant_identity="caller",
                participant_name="Phone Caller",
                play_dialtone=True,
                attributes={"call_id": call_id}  # Pour référencer l'ID d'appel dans Xano
            )
            
            response = await self.livekit_api.sip.create_sip_participant(request)
            
            # Notifier Xano du début de l'appel
            await self._send_call_event_to_xano(call_id, "dialing", response.sid)
            
            return {
                "participant_id": response.sid,
                "room_name": response.room_name,
                "status": "dialing"
            }
        except Exception as e:
            logger.error(f"Error making outbound call: {e}")
            # Notifier Xano de l'échec
            await self._send_call_event_to_xano(call_id, "failed", None, error=str(e))
            return {"status": "error", "error": str(e)}
            
    async def _send_call_event_to_xano(self, call_id: str, status: str, call_sid: str = None, error: str = None):
        try:
            payload = {
                "call_id": call_id,
                "status": status,
                "call_sid": call_sid,
                "error": error
            }
            
            headers = {"X-API-Key": self.xano_api_key}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.xano_webhook_url,
                    json=payload,
                    headers=headers
                )
                
                logger.info(f"Call event sent to Xano, status: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending call event to Xano: {e}")

sip_service = SipService()
