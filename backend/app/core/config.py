"""환경 설정 — backend/.env 값을 읽어 온다."""
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "Hotel Reservation API"

    # 개발: 각자 PC의 MariaDB. 시연 DB는 미정(정해지면 .env 값만 바꾼다)
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "hotel"
    db_user: str = "root"
    db_password: str = ""

    session_secret: str
    session_cookie: str = "hotel_session"
    session_seconds: int = 60 * 60 * 8  # 8시간

    # init_db가 팀 공용 개발용 관리자 admin01을 만들 때 쓰는 비밀번호 (팀에 따로 전달, 커밋 금지)
    admin_password: str = ""

    cors_origins: str = "http://localhost:3000"
    upload_dir: str = "uploads"

    @property
    def database_url(self) -> str:
        return self.server_url + self.db_name + "?charset=utf8mb4"

    @property
    def server_url(self) -> str:
        """DB 이름 없이 서버까지만 (DB 만들기 · 지우기용)."""
        return (
            f"mysql+pymysql://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
