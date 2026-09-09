from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/app.db"
    storage_dir: str = "./data/media"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    secure_cookies: bool = False
    session_hours: int = 8
    max_upload_bytes: int = 20 * 1024 * 1024

    @property
    def origins(self) -> list[str]:
        return [v.strip() for v in self.allowed_origins.split(",") if v.strip()]


@lru_cache
def settings() -> Settings:
    return Settings()
