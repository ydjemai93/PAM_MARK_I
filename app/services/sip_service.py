import logging
import httpx
import json
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
        # Cache pour les trunks créés
        self.created_trunks = {}
    
    async def create_outbound_trunk(self, name: str, phone_number: str, auth_username: str, auth_password: str) -> Dict[str, Any]:
        try:
            # Vérifier si nous avons déjà créé un trunk pour ce numéro
            for trunk_id, trunk_info in self.created_trunks.items():
                if phone_number in trunk_info.get("numbers", []):
                    logger.info(f"Trunk existant trouvé pour {phone_number}: {trunk_id}")
                    return {
                        "trunk_id": trunk_id,
                        "name": trunk_info.get("name"),
                        "numbers": trunk_info.get("numbers"),
                        "status": "existing"
                    }
            
            # Création d'un nouveau trunk
            trunk = api.SIPOutboundTrunkInfo(
                name=name,
                address="sip.twilio.com",
                numbers=[phone_number],
                auth_username=auth_username,
                auth_password=auth_password
            )
            
            request = api.CreateSIPOutboundTrunkRequest(trunk=trunk)
            response = await self.livekit_api.sip.create_sip_outbound_trunk(request)
            
            # Stocker le trunk créé dans le cache
            self.created_trunks[response.id] = {
                "name": response.name,
                "numbers": response.numbers,
                "address": response.address
            }
            
            logger.info(f"Nouveau trunk créé: id={response.id}, name={response.name}")
            
            return {
                "trunk_id": response.id,
                "name": response.name,
                "numbers": response.numbers,
                "status": "created"
            }
        except Exception as e:
            logger.error(f"Error creating outbound trunk: {e}")
            return {"status": "error", "error": str(e)}
    
    async def list_trunks(self) -> Dict[str, Any]:
        """Lister tous les trunks SIP outbound disponibles"""
        try:
            # Créer une requête vide pour lister les trunks
            request = api.ListSIPOutboundTrunkRequest()
            response = await self.livekit_api.sip.list_sip_outbound_trunk(request)
            
            trunks = []
            for trunk in response.items:
                # Mettre à jour notre cache de trunks
                self.created_trunks[trunk.id] = {
                    "name": trunk.name,
                    "numbers": trunk.numbers,
                    "address": trunk.address
                }
                
                trunks.append({
                    "id": trunk.id,
                    "name": trunk.name,
                    "address": trunk.address,
                    "numbers": trunk.numbers
                })
            
            logger.info(f"Trunks SIP disponibles: {trunks}")
            return {"status": "success", "trunks": trunks}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des trunks: {e}")
            return {"status": "error", "error": str(e)}
    
    async def make_outbound_call(self, trunk_id: str, phone_number: str, room_name: str, call_id: str) -> Dict[str, Any]:
        try:
            # Vérifier d'abord les trunks disponibles
            trunks_result = await self.list_trunks()
            
            # Même si le trunk spécifié n'existe pas, nous allons en créer un nouveau
            if trunks_result.get("status") == "success":
                trunk_ids = [trunk["id"] for trunk in trunks_result.get("trunks", [])]
                if trunk_id not in trunk_ids:
                    logger.warning(f"Le trunk ID {trunk_id} n'existe pas dans LiveKit. Création d'un nouveau trunk.")
                    
                    # Configuration pour Twilio à partir des variables d'environnement
                    twilio_username = settings.twilio_account_sid
                    twilio_password = settings.twilio_auth_token
                    twilio_number = settings.twilio_phone_number
                    
                    # Créer un nouveau trunk avec les informations de Twilio
                    new_trunk_result = await self.create_outbound_trunk(
                        name=f"Auto Trunk for {phone_number}",
                        phone_number=twilio_number,
                        auth_username=twilio_username,
                        auth_password=twilio_password
                    )
                    
                    if new_trunk_result.get("status") in ["created", "existing"]:
                        trunk_id = new_trunk_result.get("trunk_id")
                        logger.info(f"Nouveau trunk créé: {trunk_id}")
                    else:
                        logger.error(f"Échec de création du trunk: {new_trunk_result}")
                        raise ValueError(f"Impossible de créer un trunk pour {phone_number}")
            
            # Log des informations d'appel
            logger.info(f"Tentative d'appel avec: trunk_id={trunk_id}, phone={phone_number}, room={room_name}")
            
            # Utiliser le format exact adapté à la version de l'API LiveKit
            request = api.CreateSIPParticipantRequest()
            request.sip_trunk_id = trunk_id
            request.sip_call_to = phone_number
            request.room_name = room_name
            
            # Création du participant SIP
            response = await self.livekit_api.sip.create_sip_participant(request)
            
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
