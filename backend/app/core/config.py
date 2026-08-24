import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve absolute path to the project root directory where .env is located
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
ENV_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    GROQ_API_KEY: str = "mock-key-for-local-testing"
    GROQ_TRANSCRIPTION_MODEL: str = "whisper-large-v3-turbo"
    GROQ_LLM_MODEL: str = "llama-3.3-70b-versatile"
    MAX_AUDIO_SIZE_MB: int = 100
    DATABASE_URL: str = "sqlite:///./meeting_summarizer.db"
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
