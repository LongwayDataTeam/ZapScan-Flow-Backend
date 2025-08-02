import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Fulfillment Tracking System"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./fulfillment_tracking.db",
        env="DATABASE_URL"
    )
    
    # Supabase Configuration
    SUPABASE_URL: str = Field(
        default="",
        env="SUPABASE_URL"
    )
    SUPABASE_ANON_KEY: str = Field(
        default="",
        env="SUPABASE_ANON_KEY"
    )
    SUPABASE_DB_PASSWORD: str = Field(
        default="",
        env="SUPABASE_DB_PASSWORD"
    )
    
    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis (Optional for local development)
    REDIS_URL: str = Field(
        default="",
        env="REDIS_URL"
    )
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".csv", ".xlsx", ".xls"}
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Fulfillment Tracking API"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://localhost:8080",
        "https://zapscan-flow-frontend.vercel.app",
        "https://zapscan-flow.vercel.app"
    ]
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    
    # Google Sheets Configuration
    GOOGLE_SHEETS_SPREADSHEET_ID: str = Field(
        default="1rLSCtZkVU3WJ8qQz1l5Tv3L6aaAuqf_iKGaKaLMh2zQ",
        env="GOOGLE_SHEETS_SPREADSHEET_ID"
    )
    GOOGLE_SHEETS_CREDENTIALS_PATH: str = Field(
        default="gsheet-onescan-service.json",
        env="GOOGLE_SHEETS_CREDENTIALS_PATH"
    )
    GOOGLE_SHEETS_WORKSHEET_NAME: str = Field(
        default="tracker",
        env="GOOGLE_SHEETS_WORKSHEET_NAME"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def get_database_url() -> str:
    """Get database URL with fallback to SQLite for development"""
    return settings.DATABASE_URL


def get_redis_url() -> str:
    """Get Redis URL with fallback"""
    return settings.REDIS_URL 