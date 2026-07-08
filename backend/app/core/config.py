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

    DATABASE_URL: str = "mysql+pymysql://smanager:12345678@127.0.0.1:3306/smanager?charset=utf8mb4"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    AUTH_TOKEN_EXPIRE_MINUTES: int = 720

    SERVER_API_BASE_URL: Optional[str] = None
    SERVER_API_TOKEN: Optional[str] = None
    SERVER_REQUEST_TIMEOUT: int = 30
    SERVER_RUNS_REQUEST_TIMEOUT: int = 20
    SERVER_PRODUCT_DOWNLOAD_TIMEOUT: int = 900
    SERVER_TICK_TIMEOUT: int = 3600
    TUNNEL_HEALTH_URL: Optional[str] = None
    SERVER_FNL_ROOTS: Optional[str] = None
    SERVER_FNL_REPAIR_ROOT: Optional[str] = None
    FNL_DOWNLOAD_COMMAND: Optional[str] = None
    FNL_GDEX_BASE_URL: str = "https://osdf-director.osg-htc.org/ncar/gdex/d083002/grib2"
    FNL_DOWNLOAD_MAX_RETRIES: int = 5
    FNL_DOWNLOAD_RETRY_DELAY: int = 10
    FNL_DOWNLOAD_CHUNK_SIZE: int = 262144
    FNL_UPLOAD_TIMEOUT: int = 600
    LOCAL_FNL_CACHE_DIR: str = "runtime/fnl"
    FNL_MIN_MB: float = 5.0
    LOCAL_PRODUCTS_DIR: str = "runtime/products"
    LOCAL_LOGS_DIR: str = "runtime/logs"
    LOCAL_MANIFESTS_DIR: str = "runtime/manifests"
    LOCAL_CACHE_DIR: str = "runtime/cache"
    PRODUCT_INLINE_MAX_MB: float = 512.0
    SERVER_PRODUCT_DOWNLOAD_TIMEOUT: int = 900
    NOTIFICATION_WEBHOOK_URL: Optional[str] = None
    NOTIFICATION_WEBHOOK_TIMEOUT: int = 10
    STORAGE_RETENTION_DAYS: int = 30
    STORAGE_MAX_GB: float = 50.0
    FNL_REPAIR_POLL_INTERVAL_SECONDS: int = 120

settings = Settings()
