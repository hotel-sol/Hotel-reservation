from pydantic import Field

from app.schemas.common import CamelModel


class SignupRequest(CamelModel):
    login_id: str = Field(pattern=r"^[A-Za-z0-9_]{4,50}$")
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, pattern=r"^[0-9-]{9,20}$")
    email: str | None = Field(default=None, max_length=100)


class LoginRequest(CamelModel):
    login_id: str
    password: str


class ProfileUpdate(CamelModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)


class PasswordChange(CamelModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)


class WithdrawRequest(CamelModel):
    password: str


class PasswordResetRequest(CamelModel):
    login_id: str
    email: str
    new_password: str = Field(min_length=8, max_length=100)


class MemberOut(CamelModel):
    member_id: int
    login_id: str
    name: str
    phone: str | None
    email: str | None
    role: str
