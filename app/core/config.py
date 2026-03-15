from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SysConta API"
    environment: str = "dev"
    secret_key: str = "change-me-in-production"
    token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite:///./sysconta.db"
    cors_origins: list[str] = ["*"]
    auto_seed_admin: bool = True
    seed_admin_name: str = "Administrador"
    seed_admin_email: str = "admin@sysconta.com"
    seed_admin_password: str = "Admin@123456"
    seed_company_name: str = "Empresa Principal"
    seed_company_cnpj: str = "00000000000191"
    seed_admin_update_password: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
