from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./poker.db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    
    class Config:
        env_file = ".env"

settings = Settings()
