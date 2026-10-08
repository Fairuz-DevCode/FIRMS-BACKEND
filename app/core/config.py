import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int = int(os.getenv("PORT", "5000"))
    DB_HOST: str = os.getenv("DB_HOST", "db")
    DB_USER: str = os.getenv("DB_USER", "firms_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "firms_password")
    DB_NAME: str = os.getenv("DB_NAME", "firms_db")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    
    @property
    def DATABASE_URL(self) -> str:
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        env_url = os.getenv("ASYNC_DATABASE_URL")
        if env_url:
            return env_url
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
