from pydantic import Field

from app.schemas.common import CamelModel


# 아이디 4~20자(일반 호텔 · 쇼핑몰과 비슷하게), 비밀번호 8~64자(긴 문장 비밀번호는 허용: NIST 권고 64자 이상)
class SignupRequest(CamelModel):
    login_id: str = Field(pattern=r"^[A-Za-z0-9_]{4,20}$")
    password: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, pattern=r"^[0-9-]{9,20}$")
    email: str | None = Field(default=None, max_length=100)


class IdCheckOut(CamelModel):
    available: bool
    message: str


# 길이 상한: 너무 긴 값은 DB까지 가지 않게(잠금 기록 attempt_key 80자 초과 → 500 막기).
# 예전 규칙(아이디 50자 · 비밀번호 100자)으로 가입한 사람도 로그인할 수 있게 그때 상한을 둔다
class LoginRequest(CamelModel):
    login_id: str = Field(max_length=50)
    password: str = Field(max_length=100)


class ProfileUpdate(CamelModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)


class PasswordChange(CamelModel):
    current_password: str = Field(max_length=100)
    new_password: str = Field(min_length=8, max_length=64)


class WithdrawRequest(CamelModel):
    password: str = Field(max_length=100)


class MemberOut(CamelModel):
    member_id: int
    login_id: str
    name: str
    phone: str
    email: str | None
    role: str
