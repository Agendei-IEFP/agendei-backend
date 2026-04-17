from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    env: str = "development"
    database_url: str
    database_url_test: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_expiration_minutes: int
    refresh_token_expire_days: int
    allowed_origins: list[str]
    current_terms_version: str


settings = Settings()  # type: ignore[call-arg]
