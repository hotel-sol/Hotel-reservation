from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# 3-A2 사유 분류 (DDL ck_closure_reason_code 와 같은 값)
REASON_CODES = ("CONSTRUCTION", "MAINTENANCE", "EVENT", "CLOSURE", "ETC")
REASON_LABELS = {"CONSTRUCTION": "공사", "MAINTENANCE": "점검", "EVENT": "행사", "CLOSURE": "휴관", "ETC": "기타"}


def closure_label(code: str, detail: str | None) -> str:
    """화면 표시용 사유: "점검 · 보일러", 기타는 상세만."""
    return (detail or "") if code == "ETC" else " · ".join(filter(None, [REASON_LABELS[code], detail]))


class Closure(Base):
    """휴무 묶음(3-A1) — 한 번에 지정한 기간 하나. 날짜 행(closed_date)이 closure_id 로 묶인다."""

    __tablename__ = "closure"

    closure_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reason_code: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Unicode(200))
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("member.member_id"))  # 3-A3
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
