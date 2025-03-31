import logging
import httpx
import time
from typing import Dict, Any
from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest, SIPParticipantInfo
from app.core.config import settings

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
        """
        Crée un trunk SIP outbound pour les appels sortants
        """
        try:
            logger.info(f"Création d'un trunk avec: name={name}, phone={phone_number}, username={auth_username}")
            
            # Création du trunk
            trunk = api.SIPOutboundTrunkInfo(
                name=name,
                address="sip.twilio.com",  # Adresse du serveur SIP Twilio
                numbers=[phone_number],
                auth_username=auth_username,
                auth_password=auth_password
            )
            
            request = api.CreateSIPOutboundTrunkRequest(trunk=trunk)
            trunk_info = await self.livekit_api.sip.create_sip_outbound_trunk(request)
            
            # Générer un ID pour le trunk
            trunk_id = getattr(trunk_info, 'id', f"trunk-{int(time.time())}")
            
            logger.info(f"Trunk créé avec succès: id={trunk_id}, name={name}")
            
            return {
                "trunk_id": trunk_id,
                "name": name,
                "numbers": [phone_number],
                "status": "created"
            }
        except Exception as e:
            logger.error(f"Erreur lors de la création du trunk: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def make_outbound_call(self, trunk_id: str, phone_number: str, room_name: str, call_id: str) -> Dict[str, Any]:
        """
        Effectue un appel sortant en utilisant un trunk SIP
        """
        try:
            logger.info(f"Initiation d'un appel: trunk={trunk_id}, phone={phone_number}, room={room_name}")
            
            # Création d'un participant SIP pour effectuer l'appel
            request = CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=phone_number,
                room_name=room_name,
                participant_identity=f"sip-{call_id}",
                participant_name="Outbound Call",
                play_dialtone=True  # Jouer une tonalité pendant que l'appel se connecte
            )
            
            # Faire l'appel
            participant = await self.livekit_api.sip.create_sip_participant(request)
            
            # Enregistrer l'ID du participant pour le suivi
            participant_id = getattr(participant, 'id', f"SIP-{call_id}")
            
            logger.info(f"Appel initié avec succès: participant_id={participant_id}, status=dialing")
            
            # Notifier Xano du début de l'appel
            await self._send_call_event_to_xano(call_id, "dialing", participant_id)
            
            return {
                "participant_id": participant_id,
                "room_name": room_name,
                "status": "dialing",
                "call_id": call_id
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'initiation de l'appel: {str(e)}")
            
            # Notifier Xano de l'échec
            await self._send_call_event_to_xano(call_id, "failed", None, error=str(e))
            
            return {
                "status": "error", 
                "error": str(e),
                "call_id": call_id
            }
            
    async def _send_call_event_to_xano(self, call_id: str, status: str, participant_id: str = None, error: str = None):
        """
        Envoie un événement d'appel à Xano pour le suivi
        """
        if not self.xano_webhook_url or not self.xano_api_key:
            logger.warning("Configuration Xano manquante, impossible d'envoyer l'événement d'appel")
            return
            
        try:
            # Préparation du payload
            payload = {
                "call_id": call_id,
                "status": status,
                "field_value": "1"  # Champ requis par Xano
            }
            
            if participant_id:
                payload["participant_id"] = participant_id
                
            if error:
                payload["error"] = error
            
            # Envoi à Xano
            headers = {
                "X-API-Key": self.xano_api_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.xano_webhook_url,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Événement d'appel envoyé à Xano: {status}")
                else:
                    logger.warning(f"Échec de l'envoi à Xano: {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi à Xano: {str(e)}")

# Instancier le service
sip_service = SipService()
