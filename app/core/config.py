import os
from typing import List
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Configuration LiveKit
    livekit_url: str = os.getenv("LIVEKIT_URL", "")
    livekit_api_key: str = os.getenv("LIVEKIT_API_KEY", "")
    livekit_api_secret: str = os.getenv("LIVEKIT_API_SECRET", "")
    
    # Configuration API
    api_secret_key: str = os.getenv("API_SECRET_KEY", "")
    
    # Configuration Xano
    xano_webhook_url: str = os.getenv("XANO_WEBHOOK_URL", "")
    xano_api_key: str = os.getenv("XANO_API_KEY", "")
    
    # Configuration Twilio
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    twilio_sip_trunk_id: str = os.getenv("TWILIO_SIP_TRUNK_ID", "")
    
    # Configuration CORS
    cors_origins: List[str] = []
    
    # Configuration de l'application
    debug: bool = os.getenv("DEBUG", "").lower() in ("true", "1", "t")
    
    # Configuration du déploiement
    port: int = int(os.getenv("PORT", "8000"))
    host: str = os.getenv("HOST", "0.0.0.0")
    
    class Config:
        env_file = ".env"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Traitement spécial pour cors_origins
        cors_string = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        if cors_string:
            self.cors_origins = [origin.strip() for origin in cors_string.split(",") if origin.strip()]
            
        # Validation des configurations essentielles
        if not self.livekit_url or not self.livekit_api_key or not self.livekit_api_secret:
            print("WARNING: LiveKit configuration is missing or incomplete")
            
        if not self.api_secret_key:
            self.api_secret_key = "default_insecure_key"
            print("WARNING: Using insecure default API key, please set API_SECRET_KEY")

settings = Settings()
