"""
Application settings and configuration.
Uses environment variables with typed defaults.
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Ensure .env is loaded from project root even when invoked from subdirectories
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
PROJECT_ROOT = ENV_FILE.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "test_rms_dev.db"
load_dotenv(ENV_FILE)


class Settings(BaseSettings):
    """Application configuration from environment variables"""

    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=False)

    # App
    app_name: str = "RMS API"
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Database
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{DEFAULT_DB_PATH.as_posix()}",
        alias="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        alias="SECRET_KEY"
    )
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # API
    api_v1_prefix: str = "/api/v1"
    enable_seed_endpoints: bool = Field(default=False, alias="ENABLE_SEED_ENDPOINTS")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", alias="LOG_FILE")
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Idempotency
    idempotency_ttl_hours: int = 48
    idempotency_cleanup_interval: int = 3600  # seconds (1 hour)
    
    # AI Explanation Layer
    ai_enabled: bool = Field(default=True, alias="AI_ENABLED")
    ai_provider: str = Field(default="gemini", alias="AI_PROVIDER")
    
    # Gemini-specific
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model_id: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL_ID")
    
    # AI Behavior
    ai_system_prompt: str = Field(
        default="You are an expert financial reconciliation analyst. Your task is to explain why a specific bank transaction likely matches (or doesn't match) an invoice. Provide a clear, concise explanation in 2-6 sentences. Also provide a confidence score from 0 to 100 indicating your confidence that this is a correct match. Respond in JSON format with fields: 'explanation' (string) and 'confidence' (integer 0-100).",
        alias="AI_SYSTEM_PROMPT"
    )
    ai_temperature: float = Field(default=0.5, alias="AI_TEMPERATURE")
    ai_max_tokens: int = Field(default=150, alias="AI_MAX_TOKENS")
    
    # Retry Configuration
    ai_max_retries: int = Field(default=3, alias="AI_MAX_RETRIES")
    ai_timeout_seconds: float = Field(default=10.0, alias="AI_TIMEOUT_SECONDS")
    
    @model_validator(mode="after")
    def validate_api_key_when_enabled(self):
        """Disable AI if GEMINI_API_KEY is missing (warn instead of fail)."""
        if self.ai_enabled and not self.gemini_api_key:
            env_key = os.getenv("GEMINI_API_KEY")
            if env_key:
                self.gemini_api_key = env_key
            else:
                logger.warning(
                    "AI_ENABLED=true but GEMINI_API_KEY not found. Disabling AI features."
                )
                self.ai_enabled = False
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
