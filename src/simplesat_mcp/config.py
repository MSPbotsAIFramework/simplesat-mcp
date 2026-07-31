from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mcp_http_port: int = 8080
    mcp_http_host: str = "0.0.0.0"
    simplesat_base_url: str = "https://api.simplesat.io"


def get_settings() -> Settings:
    return Settings()
