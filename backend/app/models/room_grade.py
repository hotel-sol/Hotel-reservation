from sqlalchemy import BigInteger, CHAR, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RoomGrade(Base):
    """객실 등급 (2-A1) — S 로얄 스위트 · A 이그제큐티브 스위트 · B 프리미어 · C 디럭스. 값은 DDL 의 INSERT 로 들어간다."""

    __tablename__ = "room_grade"

    grade_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    grade_code: Mapped[str] = mapped_column(CHAR(1), unique=True)
    grade_name: Mapped[str] = mapped_column(Unicode(50), unique=True)
    base_price: Mapped[int] = mapped_column(Integer)  # 비수기 · 시티/마운틴뷰 1박 요금 (리버뷰는 × 1.1)
    base_guest: Mapped[int] = mapped_column(Integer)  # 기본 요금에 포함되는 인원
    max_guest: Mapped[int] = mapped_column(Integer)
    area_m2: Mapped[int] = mapped_column(Integer)
    bed_type: Mapped[str | None] = mapped_column(Unicode(30))  # 등급 기본 침대 (방마다 다르면 room.bed_type)
    intro: Mapped[str | None] = mapped_column(Unicode(300))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
