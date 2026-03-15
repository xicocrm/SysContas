from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SysConta API"
    environment: str = "dev"
    secret_key: str = "change-me-in-production"
    token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite:///./sysconta.db"
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
