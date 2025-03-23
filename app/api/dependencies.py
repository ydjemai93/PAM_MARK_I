from fastapi import Depends, HTTPException, Header, status
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import logging

from app.core.config import settings
from app.core.security import verify_api_key, verify_token

logger = logging.getLogger(__name__)

async def get_current_user(auth_result: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """
    Dépendance pour récupérer les informations de l'utilisateur authentifié à partir du token.
    
    Cette fonction est utilisée comme dépendance FastAPI pour injecter l'utilisateur
    authentifié dans les routes protégées. Dans la version actuelle, nous utilisons
    simplement le résultat de la fonction verify_token, mais dans une implémentation
    plus complète, nous pourrions récupérer des informations supplémentaires sur l'utilisateur.
    
    Args:
        auth_result: Le résultat de la vérification du token
        
    Returns:
        Un dictionnaire avec les informations de l'utilisateur
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas authentifié ou n'a pas les droits nécessaires
    """
    if not auth_result or not auth_result.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated",
        )
    
    # Dans une version plus complète, vous pourriez ici récupérer
    # des informations supplémentaires sur l'utilisateur depuis une base de données
    
    return auth_result

async def xano_webhook_auth(x_api_key: Optional[str] = Header(None)) -> bool:
    """
    Dépendance pour authentifier les webhooks provenant de Xano.
    
    Cette fonction vérifie que le webhook provient bien de Xano en comparant
    la clé API fournie dans l'en-tête avec celle configurée dans les paramètres.
    
    Args:
        x_api_key: La clé API fournie dans l'en-tête X-API-Key
        
    Returns:
        True si l'authentification est réussie
        
    Raises:
        HTTPException: Si la clé API est invalide ou manquante
    """
    if not x_api_key or x_api_key != settings.xano_api_key:
        logger.warning("Invalid or missing API key in webhook request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    
    return True

async def validate_agent_data(agent_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dépendance pour valider les données d'un agent avant son déploiement.
    
    Cette fonction vérifie que les données de l'agent contiennent tous les
    champs nécessaires et sont dans un format valide.
    
    Args:
        agent_data: Les données de l'agent à valider
        
    Returns:
        Les données de l'agent validées
        
    Raises:
        HTTPException: Si les données sont invalides ou incomplètes
    """
    required_fields = ["agent_id", "name", "prompt_template"]
    
    for field in required_fields:
        if field not in agent_data or not agent_data[field]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    # Vous pourriez ajouter d'autres validations ici
    # Par exemple, vérifier que le prompt_template n'est pas trop long
    
    return agent_data

async def validate_call_data(call_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dépendance pour valider les données d'un appel avant son initialisation.
    
    Cette fonction vérifie que les données de l'appel contiennent tous les
    champs nécessaires et sont dans un format valide.
    
    Args:
        call_data: Les données de l'appel à valider
        
    Returns:
        Les données de l'appel validées
        
    Raises:
        HTTPException: Si les données sont invalides ou incomplètes
    """
    required_fields = ["agent_id", "phone_number", "trunk_id", "call_id", "worker_id"]
    
    for field in required_fields:
        if field not in call_data or not call_data[field]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    # Validation du format du numéro de téléphone
    phone_number = call_data["phone_number"]
    if not phone_number.startswith("+"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number must start with '+' and include country code"
        )
    
    # Vous pourriez ajouter d'autres validations ici
    # Par exemple, vérifier que le numéro de téléphone est dans un format valide
    
    return call_data
