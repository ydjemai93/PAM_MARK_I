import logging
import httpx
import inspect
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
            # Déboguer l'API LiveKit - inspecter l'objet CreateSIPParticipantRequest
            try:
                # Créer une instance temporaire pour inspecter les attributs (debug uniquement)
                temp_request = api.CreateSIPParticipantRequest()
                dir_result = dir(temp_request)
                logger.info(f"Attributs de CreateSIPParticipantRequest: {dir_result}")
            except Exception as inspect_err:
                logger.error(f"Erreur lors de l'inspection: {inspect_err}")
            
            # Nous allons utiliser le constructeur directement avec tous les noms
            # de paramètres possibles pour essayer de trouver la combinaison correcte
            # Nous utilisons room_name pour room_name et room
            try:
                request = api.CreateSIPParticipantRequest()
                request.sip_trunk_id = trunk_id
                request.sip_call_to = phone_number
                request.room_name = room_name  # Essayer d'abord room_name
            except Exception as e:
                logger.warning(f"Erreur avec room_name, tentative avec room: {e}")
                request = api.CreateSIPParticipantRequest()
                request.sip_trunk_id = trunk_id
                request.sip_call_to = phone_number
            
            # Laissons l'API déterminer le champ correct pour room
            # Nous allons passer les informations au format JSON
            request_json = {
                "sip_trunk_id": trunk_id,
                "sip_call_to": phone_number,
                "room_name": room_name,
            }
            
            logger.info(f"Tentative d'appel avec paramètres: {request_json}")
            
            # Création du participant SIP en utilisant le format JSON
            response = await self.livekit_api.sip.create_sip_participant(request_json)
            
            # Préparation des informations de suivi
            call_info = {
                "participant_id": response.sid,
                "room_name": response.room,
                "status": "dialing",
                "trunk_id": trunk_id,
                "phone_number": phone_number,
                "call_id": call_id,
                "field_value": "1"  # Ajout du champ requis par Xano
            }
            
            # Notifier Xano du début de l'appel
            await self._send_call_event_to_xano(call_id, "dialing", response.sid, additional_info=call_info)
            
            logger.info(f"Appel sortant initié : {call_info}")
            
            return call_info
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'appel sortant: {e}")
            
            # Log détaillé de l'exception
            logger.exception("Détails complets de l'erreur d'appel")
            
            # Préparer les informations d'erreur
            error_info = {
                "status": "error", 
                "error": str(e),
                "trunk_id": trunk_id,
                "phone_number": phone_number,
                "field_value": "1"  # Ajout du champ requis par Xano
            }
            
            # Notifier Xano de l'échec
            await self._send_call_event_to_xano(call_id, "failed", None, simple_error=str(e))
            
            return error_info
            
    async def _send_call_event_to_xano(self, call_id: str, status: str, call_sid: str = None, 
                                       simple_error: str = None, error: Any = None, additional_info: Dict[str, Any] = None):
        """
        Envoi d'événements d'appel à Xano avec des informations détaillées
        """
        try:
            # Préparation du payload avec toutes les informations disponibles
            payload = {
                "call_id": call_id,
                "status": status,
                "field_value": "1",  # Ajout d'un champ requis par Xano
                "call_sid": call_sid
            }
            
            # Ajouter l'erreur si présente
            if simple_error:
                payload["error"] = simple_error
            
            # Ajouter des informations supplémentaires si disponibles
            if additional_info:
                payload.update(additional_info)
            
            # Préparer les en-têtes avec la clé API
            headers = {
                "X-API-Key": self.xano_api_key,
                "Content-Type": "application/json"
            }
            
            # Log du payload pour débogage
            logger.debug(f"Envoi à Xano, payload: {payload}")
            
            # Envoi asynchrone à Xano
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.xano_webhook_url,
                    json=payload,
                    headers=headers
                )
                
                # Vérifier et log du statut de la réponse
                if response.status_code not in [200, 201]:
                    logger.warning(f"Échec de l'envoi de l'événement à Xano. Statut: {response.status_code}, Réponse: {response.text}")
                else:
                    logger.info(f"Événement d'appel envoyé à Xano, statut: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'événement d'appel à Xano: {e}")

# Instancier le service
sip_service = SipService()
