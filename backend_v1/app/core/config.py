"""환경 설정 — backend/.env 값을 읽어 온다."""
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "Hotel Reservation API"

    db_host: str
    db_port: int = 1433
    db_name: str
    db_user: str
    db_password: str

    session_secret: str
    session_cookie: str = "hotel_session"
    session_seconds: int = 60 * 60 * 8  # 8시간

    cors_origins: str = "http://localhost:3000"
    upload_dir: str = "uploads"

    @property
    def database_url(self) -> str:
        # pymssql 드라이버: ODBC 드라이버 설치 없이 macOS/Windows/Linux 에서 동작
        return (
            f"mssql+pymssql://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
