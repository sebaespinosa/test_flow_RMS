"""
Application settings and configuration.
Uses environment variables with typed defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application configuration from environment variables"""
    
    # App
    app_name: str = "RMS API"
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./test_rms_dev.db",
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @field_validator("ai_enabled", mode="after")
    @classmethod
    def validate_api_key_when_enabled(cls, v, info):
        """Ensure GEMINI_API_KEY is present if AI is enabled"""
        if v and not info.data.get("gemini_api_key"):
            raise ValueError(
                "GEMINI_API_KEY environment variable is required when AI_ENABLED=true"
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
