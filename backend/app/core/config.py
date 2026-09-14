from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_mode: Literal["production", "demo", "development"] = "development"
    allow_demo_seed: bool = False
    environment: Literal["development", "production"] = "development"
    database_url: str = "sqlite:///./data/app.db"
    storage_backend: Literal["local", "s3"] = "local"
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    storage_dir: str = "./data/media"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    secure_cookies: bool = False
    session_hours: int = Field(default=8, ge=1, le=24)
    max_upload_bytes: int = 20 * 1024 * 1024
    max_video_bytes: int = 100 * 1024 * 1024
    max_video_seconds: int = 60
    pose_model_path: str = "./data/models/pose_landmarker_lite.task"

    @field_validator(
        "s3_endpoint_url",
        "s3_bucket",
        "s3_access_key_id",
        "s3_secret_access_key",
        mode="before",
    )
    @classmethod
    def empty_s3_value(cls, value):
        return value or None

    @field_validator("database_url", mode="before")
    @classmethod
    def postgres_driver(cls, value):
        if isinstance(value, str):
            for prefix in ("postgresql://", "postgres://"):
                if value.startswith(prefix):
                    return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @model_validator(mode="after")
    def deployment_constraints(self):
        if self.storage_backend == "s3" and not all(
            [self.s3_bucket, self.s3_access_key_id, self.s3_secret_access_key]
        ):
            raise ValueError("Storage S3 exige bucket e credenciais do servidor.")
        if not self.origins or any("*" in origin for origin in self.origins):
            raise ValueError("Configure origens explícitas, sem wildcard.")
        for origin in self.origins:
            parts = urlsplit(origin)
            if (
                not parts.hostname
                or parts.username
                or parts.password
                or parts.query
                or parts.fragment
                or parts.path not in ("", "/")
            ):
                raise ValueError("Origem inválida: use somente esquema, host e porta.")
        if self.environment == "production":
            if not self.secure_cookies:
                raise ValueError("Produção exige SECURE_COOKIES=true.")
            if any(urlsplit(origin).scheme != "https" for origin in self.origins):
                raise ValueError("Produção exige todas as origens com HTTPS.")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Produção exige PostgreSQL.")
        return self

    @property
    def origins(self) -> list[str]:
        return [v.strip() for v in self.allowed_origins.split(",") if v.strip()]


@lru_cache
def settings() -> Settings:
    return Settings()
