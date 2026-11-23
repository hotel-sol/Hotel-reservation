"""여러 파트가 같이 쓰는 것: 오류 응답 형식, 살아 있는 예약 상태, 오늘 날짜(한국 시간)."""
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException

KST = timezone(timedelta(hours=9))
LIVE_STATUSES = ("PENDING", "APPROVED")  # 객실을 잡고 있는 예약 (대기 + 승인). CANCELED는 빈방
DUPLICATE_KEY = 1062                      # MariaDB/MySQL 중복 키 오류 번호


def fail(status: int, code: str, message: str, **extra):
    """팀 공통 오류 응답: {"detail": {"code": "영문_대문자", "message": "화면에 띄울 문장", ...}}"""
    raise HTTPException(status, detail={"code": code, "message": message, **extra})


def today_kst() -> date:
    return datetime.now(KST).date()
