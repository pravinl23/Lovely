"""
Application settings and configuration management
"""
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
from typing import Optional, Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Main application settings"""
    
    # Application
    app_name: str = Field(default="WhatsApp-Automation")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    api_base_url: str = Field(default="http://localhost:8000")
    
    # WhatsApp Configuration
    whatsapp_phone_number_id: str = Field(..., description="WhatsApp Phone Number ID")
    whatsapp_access_token: SecretStr = Field(..., description="WhatsApp Access Token")
    whatsapp_webhook_verify_token: SecretStr = Field(..., description="Webhook Verification Token")
    whatsapp_webhook_secret: SecretStr = Field(..., description="Webhook Signature Secret")
    webhook_url: str = Field(..., description="Public webhook URL")
    
    # Database
    database_url: str = Field(..., description="PostgreSQL database URL")
    vector_db_url: Optional[str] = Field(None, description="Vector database URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    
    # LLM Configuration
    openai_api_key: Optional[SecretStr] = Field(None)
    anthropic_api_key: Optional[SecretStr] = Field(None)
    llm_provider: Literal["openai", "anthropic"] = Field(default="openai")
    llm_model_name: str = Field(default="gpt-4-turbo-preview")
    
    # Security
    jwt_secret_key: SecretStr = Field(..., description="JWT Secret Key")
    encryption_key: SecretStr = Field(..., description="32 byte encryption key")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(None)
    prometheus_enabled: bool = Field(default=True)
    
    # Feature Flags
    enable_media_processing: bool = Field(default=True)
    enable_audio_transcription: bool = Field(default=True)
    enable_image_captioning: bool = Field(default=True)
    max_concurrent_conversations: int = Field(default=10)
    default_reply_delay_seconds: int = Field(default=5)  # Reduced from 30 to 5 seconds
    
    # Rate Limiting
    rate_limit_messages_per_minute: int = Field(default=30)
    rate_limit_messages_per_hour: int = Field(default=1000)
    
    # Conversation Settings
    max_context_messages: int = Field(default=20)
    max_facts_per_contact: int = Field(default=100)
    fact_decay_days: int = Field(default=90)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings() 