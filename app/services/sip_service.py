import logging
from typing import Dict, List, Optional, Any
from livekit import api
from app.core.config import settings

logger = logging.getLogger(__name__)

class SipService:
    """Service pour gérer les trunks SIP avec Twilio"""
    
    def __init__(self):
        """Initialise le service SIP avec l'API LiveKit"""
        self.livekit_api = api.LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key, 
            api_secret=settings.livekit_api_secret
        )
    
    async def create_outbound_trunk(self, 
                                   name: str, 
                                   phone_number: str, 
                                   auth_username: str, 
                                   auth_password: str) -> Dict[str, Any]:
        """
        Crée un trunk SIP sortant pour Twilio
        
        Args:
            name: Nom du trunk
            phone_number: Numéro de téléphone Twilio (format: +33xxxxxxxxx)
            auth_username: Nom d'utilisateur pour l'authentification Twilio
            auth_password: Mot de passe pour l'authentification Twilio
            
        Returns:
            Dict avec les informations du trunk créé
        """
        try:
            trunk = api.SIPOutboundTrunkInfo(
                name=name,
                address="sip.twilio.com",  # Domaine SIP Twilio standard
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
            logger.error(f"Erreur lors de la création du trunk sortant: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def create_inbound_trunk(self, name: str, phone_number: str) -> Dict[str, Any]:
        """
        Crée un trunk SIP entrant pour Twilio
        
        Args:
            name: Nom du trunk
            phone_number: Numéro de téléphone Twilio (format: +33xxxxxxxxx)
            
        Returns:
            Dict avec les informations du trunk créé
        """
        try:
            trunk = api.SIPInboundTrunkInfo(
                name=name,
                numbers=[phone_number],
                krisp_enabled=True  # Activation de la suppression de bruit
            )
            
            request = api.CreateSIPInboundTrunkRequest(trunk=trunk)
            response = await self.livekit_api.sip.create_sip_inbound_trunk(request)
            
            return {
                "trunk_id": response.id,
                "name": response.name,
                "numbers": response.numbers,
                "status": "created"
            }
        except Exception as e:
            logger.error(f"Erreur lors de la création du trunk entrant: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def create_dispatch_rule(self, name: str, agent_name: str) -> Dict[str, Any]:
        """
        Crée une règle de dispatch pour les appels entrants
        
        Args:
            name: Nom de la règle
            agent_name: Nom de l'agent à dispatcher
            
        Returns:
            Dict avec les informations de la règle créée
        """
        try:
            # Configuration pour placer les appels dans des salles individuelles
            rule = api.SIPDispatchRule(
                dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                    room_prefix="call-"
                )
            )
            
            # Configuration de l'agent à dispatcher
            room_config = api.RoomConfigRequest(
                agents=[api.RoomAgentDispatch(
                    agent_name=agent_name
                )]
            )
            
            request = api.CreateSIPDispatchRuleRequest(
                name=name,
                rule=rule,
                room_config=room_config
            )
            
            response = await self.livekit_api.sip.create_sip_dispatch_rule(request)
            
            return {
                "rule_id": response.id,
                "name": response.name,
                "status": "created"
            }
        except Exception as e:
            logger.error(f"Erreur lors de la création de la règle de dispatch: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def make_outbound_call(self, 
                                trunk_id: str, 
                                phone_number: str, 
                                room_name: str) -> Dict[str, Any]:
        """
        Effectue un appel sortant via Twilio
        
        Args:
            trunk_id: ID du trunk SIP sortant
            phone_number: Numéro à appeler (format: +33xxxxxxxxx)
            room_name: Nom de la salle LiveKit pour l'appel
            
        Returns:
            Dict avec les informations de l'appel
        """
        try:
            request = api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_dial_to=phone_number,
                room_name=room_name,
                participant_identity="caller",
                participant_name="Phone Caller",
                play_dialtone=True
            )
            
            response = await self.livekit_api.sip.create_sip_participant(request)
            
            return {
                "participant_id": response.sid,
                "room_name": response.room_name,
                "status": "dialing"
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'appel sortant: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

# Initialiser le service pour l'utiliser dans l'application
sip_service = SipService()
