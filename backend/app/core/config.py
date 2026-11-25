"""환경 설정 — backend/.env 값을 읽어 온다."""
import re
import warnings
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SHARED_SCHEMA = "hotel"  # 시연 · 통합 확인용 공용 스키마
MIN_SECRET_LENGTH = 32  # 세션 서명 키 최소 길이 (#70)
WEAK_SECRETS = {"", "change-me"}  # .env.example 기본값 등


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "Hotel Reservation API"

    # Supabase(PostgreSQL) 접속 주소: 프로젝트 Connect → Session pooler URI (비밀번호 포함, 커밋 금지)
    database_url: str = ""
    # 테이블이 들어 있는 스키마. 팀 Supabase 프로젝트 하나를 5명이 같이 쓰므로 스키마로 나눈다.
    #   hotel          = 시연 · 통합 확인용 공용 (기본값)
    #   hotel_<이름>   = 각자 개발용,  테스트는 자동으로 <내 스키마>_test
    # (Supabase 기본 public을 건드리지 않고, REST API에도 노출되지 않는 전용 스키마)
    db_schema: str = SHARED_SCHEMA
    # true 일 때만 init_db · 테스트가 스키마를 지우고 다시 만든다. 공용 hotel 은 이 값과 상관없이 --reset-shared 필요
    db_reset_allowed: bool = False

    session_secret: str
    session_cookie: str = "hotel_session"
    session_seconds: int = 60 * 60 * 8  # 8시간

    # init_db가 팀 공용 개발용 관리자 admin01을 만들 때 쓰는 비밀번호 (팀에 따로 전달, 커밋 금지)
    admin_password: str = ""

    cors_origins: str = "http://localhost:3000"
    upload_dir: str = "uploads"

    # 2-A2 객실 사진 공용 저장소 (Supabase Storage). 주소 · 키가 둘 다 있을 때만 쓰고, 비어 있으면 upload_dir 에 저장
    supabase_url: str = ""  # https://<프로젝트>.supabase.co
    supabase_secret_key: str = ""  # Project Settings → API Keys → Secret keys (커밋 금지)
    storage_bucket: str = "room-photos"  # 누구나 읽기만 가능한(public) 버킷

    @property
    def storage_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_secret_key)

    @field_validator("db_schema")
    @classmethod
    def schema_is_identifier(cls, v: str) -> str:
        # SQL 문장에 그대로 들어가므로 영문 소문자 · 숫자 · _ 만 허용
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", v):
            raise ValueError("DB_SCHEMA 는 영문 소문자 · 숫자 · _ 만 쓸 수 있습니다.")
        return v

    @model_validator(mode="after")
    def session_secret_is_strong(self) -> "Settings":
        """#70: 세션 서명 키가 예시 값(change-me)이거나 너무 짧으면 쿠키를 위조당할 수 있다.
        시연 · 배포(APP_ENV 가 local 이 아님)는 서버 시작을 거부하고, 내 컴퓨터(local)는 경고만 한다."""
        weak = self.session_secret in WEAK_SECRETS or len(self.session_secret) < MIN_SECRET_LENGTH
        if weak and self.app_env != "local":
            raise ValueError(f"SESSION_SECRET 이 약합니다. 예시 값이 아닌 {MIN_SECRET_LENGTH}자 이상 무작위 값을 쓰세요.")
        if weak:
            warnings.warn(f"SESSION_SECRET 이 약합니다(로컬이라 계속). 배포 전 {MIN_SECRET_LENGTH}자 이상 무작위 값으로 바꾸세요.",
                          UserWarning, stacklevel=2)
        return self

    @property
    def sqlalchemy_url(self) -> str:
        """Supabase가 주는 postgresql://... 주소를 psycopg 드라이버 주소로 바꾼다."""
        if not self.database_url:
            raise RuntimeError("backend/.env 에 DATABASE_URL(Supabase Session pooler URI)을 넣어 주세요.")
        url = self.database_url.replace("postgres://", "postgresql://", 1)
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        if "sslmode=" not in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
