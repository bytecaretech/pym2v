"""Settings configuration for the pym2v package."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class to handle configuration for the pym2v package."""

    model_config = SettingsConfigDict(env_prefix="eurogard_")
    base_url: str
    username: str
    password: str
    client_id: str
    client_secret: str


SETTINGS = Settings()  # type: ignore
