from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "China Pollen Forecast System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./pollen_forecast.db"

    ADMIN_PASSWORD: str = "admin123"
    SECRET_KEY: str = "your-secret-key-change-in-production"

    class Config:
        case_sensitive = True

settings = Settings()
