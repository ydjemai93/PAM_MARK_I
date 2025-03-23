from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from jose import jwt, JWTError
from app.core.config import settings
from typing import Dict, Any

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return True

async def verify_token(token: str = Depends(api_key_header)):
    try:
        # Ici vous pourriez implémenter la vérification du token JWT de Supabase
        # Pour le MVP, nous utilisons simplement une clé API comme simplication
        if token != settings.api_secret_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        
        # Dans une implémentation plus complète, vous décoderiez le token JWT
        # et retourneriez les claims (payload)
        return {"authenticated": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}",
        )
