from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./sis_dev.db"
    app_name: str = "SIS Scalability Lab"
    token_secret: str | None = Field(default=None, min_length=32, validation_alias="SIS_TOKEN_SECRET")
    environment: str = Field(default="development", validation_alias="SIS_ENV")
    rate_limit_enabled: bool = Field(default=True, validation_alias="SIS_RATE_LIMIT_ENABLED")
    cache_enabled: bool = Field(default=True, validation_alias="SIS_CACHE_ENABLED")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
