from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "智能采购管理系统"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://income:Vk7#a3DfGtYhJkL9@118.195.236.243:53890/income"
    
    # JWT
    SECRET_KEY: str = "smart-procurement-system-secret-key-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # DeepSeek API
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_API_KEY: str = "sk-0d58e31989a2447daec86f84d4f11dec"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
