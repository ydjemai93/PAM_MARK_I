import os
from typing import List
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    livekit_url: str = os.getenv("LIVEKIT_URL", "")
    livekit_api_key: str = os.getenv("LIVEKIT_API_KEY", "")
    livekit_api_secret: str = os.getenv("LIVEKIT_API_SECRET", "")
    api_secret_key: str = os.getenv("API_SECRET_KEY", "")
    xano_webhook_url: str = os.getenv("XANO_WEBHOOK_URL", "")
    xano_api_key: str = os.getenv("XANO_API_KEY", "")
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

settings = Settings()
