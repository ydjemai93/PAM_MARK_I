from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Récupère les informations de l'utilisateur authentifié depuis Supabase
    """
    token = credentials.credentials
    
    try:
        # Requête à l'API Supabase pour valider le token JWT
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.supabase_key,
                "Authorization": f"Bearer {token}"
            }
            response = await client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers=headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "id": user_data["id"],
                    "email": user_data["email"],
                    "app_metadata": user_data.get("app_metadata", {}),
                    "user_metadata": user_data.get("user_metadata", {})
                }
            else:
                logger.error(f"Failed to verify token: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication error",
            headers={"WWW-Authenticate": "Bearer"},
        )
