"""Configuracion central de la aplicacion."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAFEHOME_", env_file=".env", extra="ignore")

    app_name: str = "SafeHome Kitchen Monitor API"
    database_url: str = "sqlite:///./safehome.db"

    # Umbrales por defecto (documento, seccion 9.3 Modulo 1).
    gas_alerta_default: float = 400
    gas_emergencia_default: float = 800
    temp_max_default: float = 60


settings = Settings()
