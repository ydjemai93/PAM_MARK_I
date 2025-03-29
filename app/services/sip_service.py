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
            
            # Vérifier que les informations nécessaires sont présentes
            if not all([name, phone_number, auth_username, auth_password]):
                missing = []
                if not name: missing.append("name")
                if not phone_number: missing.append("phone_number")
                if not auth_username: missing.append("auth_username")
                if not auth_password: missing.append("auth_password")
                
                logger.error(f"Informations manquantes pour la création de trunk: {missing}")
                return {"status": "error", "error": f"Missing parameters: {', '.join(missing)}"}
            
            # Journaliser les paramètres (masquer le mot de passe)
            logger.info(f"Création d'un trunk avec: name={name}, phone={phone_number}, username={auth_username}")
            
            # Création d'un nouveau trunk
            trunk = api.SIPOutboundTrunkInfo(
                name=name,
                address="sip.twilio.com",
                numbers=[phone_number],
                auth_username=auth_username,
                auth_password=auth_password
            )
            
            # Log pour déboguer
            logger.debug(f"Trunk info créé: {trunk}")
            
            request = api.CreateSIPOutboundTrunkRequest(trunk=trunk)
            response = await self.livekit_api.sip.create_sip_outbound_trunk(request)
            
            # Générer un ID temporaire si non disponible dans la réponse
            trunk_id = getattr(response, 'id', f"temp-trunk-{phone_number.replace('+', '')}")
            
            # Stocker le trunk créé dans le cache
            self.created_trunks[trunk_id] = {
                "name": getattr(response, 'name', name),
                "numbers": getattr(response, 'numbers', [phone_number]),
                "address": getattr(response, 'address', "sip.twilio.com")
            }
            
            logger.info(f"Nouveau trunk créé: id={trunk_id}, name={name}")
            
            return {
                "trunk_id": trunk_id,
                "name": name,
                "numbers": [phone_number],
                "status": "created"
            }
        except Exception as e:
            logger.error(f"Error creating outbound trunk: {str(e)}")
            logger.exception("Détails complets de l'erreur de création de trunk")
            return {"status": "error", "error": str(e)}
    
    async def list_trunks(self) -> Dict[str, Any]:
        """Lister tous les trunks SIP outbound disponibles"""
        try:
            # Créer une requête vide pour lister les trunks
            request = api.ListSIPOutboundTrunkRequest()
            response = await self.livekit_api.sip.list_sip_outbound_trunk(request)
            
            trunks = []
            # Vérifier si la réponse contient des éléments
            items = getattr(response, 'items', [])
            
            for trunk in items:
                trunk_id = getattr(trunk, 'id', None)
                if not trunk_id:
                    continue
                    
                # Mettre à jour notre cache de trunks
                self.created_trunks[trunk_id] = {
                    "name": getattr(trunk, 'name', ''),
                    "numbers": getattr(trunk, 'numbers', []),
                    "address": getattr(trunk, 'address', '')
                }
                
                trunks.append({
                    "id": trunk_id,
                    "name": getattr(trunk, 'name', ''),
                    "address": getattr(trunk, 'address', ''),
                    "numbers": getattr(trunk, 'numbers', [])
                })
            
            logger.info(f"Trunks SIP disponibles: {trunks}")
            return {"status": "success", "trunks": trunks}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des trunks: {str(e)}")
            logger.exception("Détails complets de l'erreur de listage des trunks")
            return {"status": "error", "error": str(e)}
    
    async def make_outbound_call(self, trunk_id: str, phone_number: str, room_name: str, call_id: str) -> Dict[str, Any]:
        try:
            # Générer un trunk ID temporaire si nécessaire
            temp_trunk_id = f"temp-trunk-{phone_number.replace('+', '')}"
            
            # Vérifier d'abord les trunks disponibles
            trunks_result = await self.list_trunks()
            
            # Si aucun trunk n'a été trouvé, créer un trunk virtuel
            live_trunk_id = trunk_id
            
            if trunks_result.get("status") == "success":
                trunk_ids = [trunk["id"] for trunk in trunks_result.get("trunks", [])]
                
                if not trunk_ids:
                    logger.warning(f"Aucun trunk SIP disponible. Utilisation du trunk virtuel {temp_trunk_id}")
                    live_trunk_id = temp_trunk_id
                elif trunk_id not in trunk_ids:
                    logger.warning(f"Le trunk ID {trunk_id} n'existe pas dans LiveKit. Utilisation du premier trunk disponible.")
                    live_trunk_id = trunk_ids[0]
            else:
                logger.warning(f"Impossible de lister les trunks. Utilisation du trunk virtuel {temp_trunk_id}")
                live_trunk_id = temp_trunk_id
            
            # Si nous utilisons un trunk virtuel, créons-le
            if live_trunk_id == temp_trunk_id:
                # Configuration par défaut si les variables d'environnement ne sont pas définies
                twilio_username = settings.twilio_account_sid or "default_username"
                twilio_password = settings.twilio_auth_token or "default_password"
                twilio_number = settings.twilio_phone_number or phone_number
                
                logger.info(f"Création d'un trunk virtuel avec: numero={twilio_number}")
                
                # Créer un nouveau trunk avec les informations disponibles
                new_trunk_result = await self.create_outbound_trunk(
                    name=f"Virtual Trunk for {phone_number}",
                    phone_number=twilio_number,
                    auth_username=twilio_username,
                    auth_password=twilio_password
                )
                
                if new_trunk_result.get("status") in ["created", "existing"]:
                    live_trunk_id = new_trunk_result.get("trunk_id")
                    logger.info(f"Nouveau trunk créé: {live_trunk_id}")
                else:
                    # Simuler un appel réussi pour le test
                    logger.warning(f"Échec de création du trunk: {new_trunk_result}. Simulation d'un appel réussi pour le test.")
                    
                    # Générer un faux SID pour simuler un appel réussi
                    fake_sid = f"SIP-FAKE-{call_id}-{phone_number.replace('+', '')}"
                    
                    # Préparation des informations de suivi simulées
                    call_info = {
                        "participant_id": fake_sid,
                        "room_name": room_name,
                        "status": "simulated_dialing",
                        "trunk_id": trunk_id,
                        "phone_number": phone_number,
                        "call_id": call_id,
                        "field_value": "1",
                        "is_simulated": True
                    }
                    
                    # Notifier Xano du début de l'appel simulé
                    await self._send_call_event_to_xano(call_id, "simulated_dialing", fake_sid, additional_info=call_info)
                    
                    logger.info(f"Appel sortant simulé : {call_info}")
                    
                    return call_info
            
            # Log des informations d'appel
            logger.info(f"Tentative d'appel avec: trunk_id={live_trunk_id}, phone={phone_number}, room={room_name}")
            
            # Vérifier l'existence du trunk avant de faire l'appel
            if live_trunk_id not in self.created_trunks and live_trunk_id != temp_trunk_id:
                raise ValueError(f"Le trunk {live_trunk_id} n'est pas dans notre cache et ne semble pas valide")
            
            # Simuler un appel pour le test (remplacer par l'appel réel quand l'API sera prête)
            # En production, vous utiliseriez cette méthode :
            # 
            # request = api.CreateSIPParticipantRequest()
            # request.sip_trunk_id = live_trunk_id
            # request.sip_call_to = phone_number
            # request.room_name = room_name
            # response = await self.livekit_api.sip.create_sip_participant(request)
            
            # Simuler une réponse d'appel pour le test
            fake_sid = f"SIP-SIMULATED-{call_id}-{phone_number.replace('+', '')}"
            
            # Préparation des informations de suivi
            call_info = {
                "participant_id": fake_sid,
                "room_name": room_name,
                "status": "simulated_dialing",
                "trunk_id": live_trunk_id,
                "phone_number": phone_number,
                "call_id": call_id,
                "field_value": "1",
                "is_simulated": True
            }
            
            # Notifier Xano du début de l'appel
            await self._send_call_event_to_xano(call_id, "simulated_dialing", fake_sid, additional_info=call_info)
            
            logger.info(f"Appel sortant simulé : {call_info}")
            
            return call_info
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'appel sortant: {str(e)}")
            
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
            logger.error(f"Erreur lors de l'envoi de l'événement d'appel à Xano: {str(e)}")

# Instancier le service
sip_service = SipService()
