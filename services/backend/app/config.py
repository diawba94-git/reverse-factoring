from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

def _find_root_env_file() -> Path | None:
    # Walks up from this file looking for the repo-root .env. In Docker, only
    # services/backend is mounted, so no .env is found and compose's own
    # env_file injection (already in the process environment) takes over.
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


_ROOT_ENV_FILE = _find_root_env_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ROOT_ENV_FILE, extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MFA_ISSUER_NAME: str = "InvoiceUp"

    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000"

    WAVE_WEBHOOK_SECRET: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
