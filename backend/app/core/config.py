from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "China Pollen Forecast System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./pollen_forecast.db"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    AUTH_TOKEN_EXPIRE_MINUTES: int = 720

    SERVER_SSH_HOST: Optional[str] = None
    SERVER_SSH_USER: Optional[str] = None
    SERVER_SSH_PASSWORD: Optional[str] = None
    SERVER_SSH_PORT: int = 22
    SERVER_PYTHON_BIN: str = "python3"
    SERVER_FLOWCTL_PATH: str = "~/auto-pollen-flow/flowctl.py"
    SERVER_FLOW_WORKDIR: Optional[str] = None
    SERVER_FLOW_ROOT: Optional[str] = None
    SERVER_COMMANDS_FILE: Optional[str] = None
    SERVER_FNL_ROOTS: Optional[str] = None
    SERVER_FNL_UPLOAD_DIR: Optional[str] = None
    SERVER_SSH_TIMEOUT: int = 20
    FNL_DOWNLOAD_COMMAND: Optional[str] = None
    JUMPBOX_FNL_CACHE_DIR: str = "runtime/fnl"
    FNL_MIN_MB: float = 5.0
    FNL_UPLOAD_METHOD: str = "rsync"
    JUMPBOX_PRODUCTS_DIR: str = "runtime/products"
    JUMPBOX_LOGS_DIR: str = "runtime/logs"
    JUMPBOX_MANIFESTS_DIR: str = "runtime/manifests"
    JUMPBOX_CACHE_DIR: str = "runtime/cache"
    PRODUCT_SYNC_METHOD: str = "rsync"
    PRODUCT_INLINE_MAX_MB: float = 20.0
    NOTIFICATION_WEBHOOK_URL: Optional[str] = None
    NOTIFICATION_WEBHOOK_TIMEOUT: int = 10
    STORAGE_RETENTION_DAYS: int = 30
    STORAGE_MAX_GB: float = 50.0
    AGENT_MAX_AUTO_ACTIONS_PER_RUN: int = 3
    AGENT_TICK_INTERVAL_MINUTES: int = 30

settings = Settings()
