from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Unicode, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AttachFile(Base):
    """첨부파일 (공통) — target_type + target_id 로 주인 표시 (예: 'ROOM', 3)"""

    __tablename__ = "attach_file"

    file_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int] = mapped_column(BigInteger)
    original_name: Mapped[str] = mapped_column(Unicode(255))
    saved_path: Mapped[str] = mapped_column(Unicode(500))
    file_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
