"""오늘 날짜는 한국 시간 기준 (서버가 외국 시간대여도 같게)."""
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    return datetime.now(KST).date()
