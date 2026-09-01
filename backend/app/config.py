import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Mahindra Intelligent Assistant (MIA) with Kabir AI"
    API_V1_STR: str = "/api"
    VERTEX_PROJECT_ID: str = os.getenv("VERTEX_PROJECT_ID", os.getenv("PROJECT_ID", "mb-poc-352009"))
    VERTEX_LOCATION: str = os.getenv("VERTEX_LOCATION", os.getenv("LOCATION", "us-central1"))
    
    # Live Bidi WebSocket Configuration (Gemini Live 2.5 Native Audio)
    GEMINI_LIVE_MODEL: str = os.getenv("GEMINI_LIVE_MODEL", "gemini-live-2.5-flash-native-audio")
    BIDI_SERVICE_URL: str = "wss://{host}/ws/google.cloud.aiplatform.internal.LlmBidiService/BidiGenerateContent"
    
    # REST Chat Model (Standard GenerateContent)
    REST_CHAT_MODEL: str = os.getenv("REST_CHAT_MODEL", "gemini-2.5-flash")
    
    AVATAR_VOICE: str = os.getenv("AVATAR_VOICE", "Aoede") # Voice for Kavya (Female Indian AI Specialist)
    AVATAR_NAME: str = os.getenv("AVATAR_NAME", "Kavya")
    AVATAR_MODALITY: str = os.getenv("AVATAR_MODALITY", "AUDIO") # Real-time native live audio stream
    DEFAULT_LOCALE: str = os.getenv("DEFAULT_LOCALE", "hi-IN") # Multilingual
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:MahindraDev2026!Secure@34.42.54.228:5432/mahindra_auto")
    GCS_RECORDINGS_BUCKET: str = os.getenv("GCS_RECORDINGS_BUCKET", os.getenv("GCS_BUCKET", "mb-poc-352009-sales-recordings"))
    WS_LIVE_AUDIO_PATH: str = "/ws/live-audio"
    DEFAULT_DEALERSHIP: str = "Bayview Mahindra, Bandra West, Mumbai"    
    
    # SMS Dispatch Configuration (Configurable via Cloud Run environment variable)
    ENABLE_SMS_DISPATCH: bool = os.getenv("ENABLE_SMS_DISPATCH", "true").lower() in ("true", "1", "yes")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="allow")

settings = Settings()
