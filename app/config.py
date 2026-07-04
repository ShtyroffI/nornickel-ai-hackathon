from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "nornickel_knowledge"
    postgres_user: str = "nornickel"
    postgres_password: str = "nornickel"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "nornickel"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    nlp_provider: str = "stub"
    log_level: str = "INFO"
    
    yandex_api_key: str = ""
    yandex_folder_id: str = ""

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
