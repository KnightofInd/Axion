from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AXION API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    axion_internal_api_key: str = "replace-me"

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_db_schema: str = "public"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    google_cloud_project: str = "axion-prod"
    google_cloud_region: str = "us-central1"
    gemini_api_key: str = ""
    vertex_embedding_model: str = "text-embedding-005"
    gemini_flash_model: str = "gemini-2.0-flash"
    gemini_pro_model: str = "gemini-1.5-pro"

    allow_origin: str = "http://localhost:3000"

    @field_validator("*", mode="before")
    @classmethod
    def strip_string_values(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


settings = Settings()
