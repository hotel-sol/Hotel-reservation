from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Unicode, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Member(Base):
    """회원 — role: USER(손님) / ADMIN(관리자)"""

    __tablename__ = "member"

    member_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    login_id: Mapped[str] = mapped_column(Unicode(50), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(Unicode(50))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(10), server_default="USER")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
