from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./sis_dev.db"
    app_name: str = "SIS Scalability Lab"
    token_secret: str | None = Field(default=None, min_length=32, validation_alias="SIS_TOKEN_SECRET")
    environment: str = Field(default="development", validation_alias="SIS_ENV")
    rate_limit_enabled: bool = Field(default=True, validation_alias="SIS_RATE_LIMIT_ENABLED")

    # Redis holds all shared mutable state: the rate-limit buckets, the autocomplete cache
    # and the worker-id counter. Every app process talks to the same instance, so limits and
    # cache hits are enforced across replicas instead of per process.
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", validation_alias="SIS_REDIS_URL")
    rate_limit_capacity: int = Field(default=120, gt=0, validation_alias="SIS_RATE_LIMIT_CAPACITY")
    rate_limit_refill_per_second: float = Field(
        default=10.0, gt=0, validation_alias="SIS_RATE_LIMIT_REFILL_PER_SECOND"
    )
    cache_ttl_seconds: int = Field(default=20, gt=0, validation_alias="SIS_CACHE_TTL_SECONDS")

    # mongos router address. The sharded records live behind this router, which owns chunk
    # placement; the application never talks to a shard directly.
    mongo_uri: str = Field(default="mongodb://127.0.0.1:27017", validation_alias="SIS_MONGO_URI")
    mongo_db: str = Field(default="sis", validation_alias="SIS_MONGO_DB")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
