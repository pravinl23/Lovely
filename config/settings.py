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
    
    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: SecretStr = Field(..., description="Supabase anonymous key")
    supabase_service_role_key: SecretStr = Field(..., description="Supabase service role key")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # LLM Configuration
    openai_api_key: SecretStr = Field(..., description="OpenAI API key")
    llm_model_name: str = Field(default="gpt-4-turbo-preview")
    llm_provider: str = Field(default="openai", description="LLM provider (openai, anthropic, etc.)")
    
    # Security
    jwt_secret_key: SecretStr = Field(..., description="JWT Secret Key")
    encryption_key: SecretStr = Field(..., description="32 byte encryption key")
    
    # Feature Flags
    max_concurrent_conversations: int = Field(default=10)
    default_reply_delay_seconds: int = Field(default=1)
    
    # Rate Limiting
    rate_limit_messages_per_minute: int = Field(default=30)
    rate_limit_messages_per_hour: int = Field(default=1000)
    
    # Conversation Settings
    max_context_messages: int = Field(default=20)
    max_facts_per_contact: int = Field(default=100)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields during transition


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings() 