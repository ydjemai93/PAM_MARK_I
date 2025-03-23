import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

class Settings(BaseSettings):
    """Settings de l'application"""
    
    # Général
    app_name: str = "AI Phone Agent API"
    debug: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    secret_key: str = os.getenv("SECRET_KEY", "dev_secret_key")
    
    # Base de données
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
    
    # LiveKit
    livekit_url: str = os.getenv("LIVEKIT_URL", "")
    livekit_api_key: str = os.getenv("LIVEKIT_API_KEY", "")
    livekit_api_secret: str = os.getenv("LIVEKIT_API_SECRET", "")
    
    # Services IA
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")
    cartesia_api_key: str = os.getenv("CARTESIA_API_KEY", "")
    
    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")
    
    # Twilio
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    twilio_sip_trunk_id: str = os.getenv("TWILIO_SIP_TRUNK_ID", "")
    twilio_sip_username: str = os.getenv("TWILIO_SIP_USERNAME", "")
    twilio_sip_password: str = os.getenv("TWILIO_SIP_PASSWORD", "")
    
    # CORS
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # JWT
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 jours
    
    class Config:
        case_sensitive = True

# Instance des settings
settings = Settings()
