from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str

    postgres_user: str = "newsbot"
    postgres_password: str = "newsbot_secret"
    postgres_db: str = "newsbot"
    postgres_host: str = "db"
    postgres_port: int = 5432

    scrape_interval_seconds: int = 300

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()  # type: ignore[call-arg]
