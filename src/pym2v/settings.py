"""Settings configuration for the pym2v package."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class to handle configuration for the pym2v package."""

    model_config = SettingsConfigDict(env_prefix="eurogard_", env_file=".env")
    base_url: str
    username: str
    password: SecretStr
    client_id: str
    client_secret: SecretStr
