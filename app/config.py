"""Configuracion central de la aplicacion."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAFEHOME_", env_file=".env", extra="ignore")

    app_name: str = "SafeHome Kitchen Monitor API"
    database_url: str = "sqlite:///./safehome.db"

    # Umbrales por defecto (circuit.md).
    gas_alerta_default: float = 1000
    gas_emergencia_default: float = 2000
    temp_warning_default: float = 55
    temp_max_default: float = 70


settings = Settings()
