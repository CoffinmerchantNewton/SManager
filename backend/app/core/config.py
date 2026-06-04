from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "China Pollen Forecast System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./pollen_forecast.db"

    ADMIN_PASSWORD: str = "admin123"
    SECRET_KEY: str = "your-secret-key-change-in-production"

    SERVER_SSH_HOST: Optional[str] = None
    SERVER_SSH_USER: Optional[str] = None
    SERVER_SSH_PORT: int = 22
    SERVER_FLOWCTL_PATH: str = "~/auto-pollen-flow/flowctl.py"
    SERVER_FLOW_WORKDIR: Optional[str] = None
    SERVER_FLOW_ROOT: Optional[str] = None
    SERVER_FNL_ROOTS: Optional[str] = None
    SERVER_FNL_UPLOAD_DIR: Optional[str] = None
    SERVER_SSH_TIMEOUT: int = 20
    FNL_DOWNLOAD_COMMAND: Optional[str] = None
    JUMPBOX_FNL_CACHE_DIR: str = "runtime/fnl"
    FNL_MIN_MB: float = 5.0
    FNL_UPLOAD_METHOD: str = "rsync"
    JUMPBOX_PRODUCTS_DIR: str = "runtime/products"
    PRODUCT_SYNC_METHOD: str = "rsync"

    class Config:
        case_sensitive = True

settings = Settings()
