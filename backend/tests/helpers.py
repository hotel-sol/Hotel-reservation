"""테스트에서 휴무 · 예약 행을 직접 넣을 때는 이 두 함수만 쓴다 (Discussion #60 규칙 R2).

DB에 칸 · 제약이 더해져도 여기 한 곳만 고치면 모든 파트 테스트가 그대로 돈다. 이 파일은 DB 담당이 고친다(R1).
"""
from datetime import date, datetime, timedelta

from sqlalchemy import text

from app.db.session import engine

LIVE = ("PENDING", "APPROVED")


def add_closed_date(day: date, room_id: int | None = None, reason: str = "테스트",
                    reason_code: str = "MAINTENANCE") -> int:
    """휴무 하루를 묶음(closure) 하나로 넣는다. room_id 가 None 이면 호텔 전체 휴무. closure_id 를 돌려준다."""
    with engine.begin() as conn:
        closure_id = conn.execute(
            text("INSERT INTO closure (reason_code, reason) VALUES (:code, :reason) RETURNING closure_id"),
            {"code": reason_code, "reason": reason},
        ).scalar_one()
        conn.execute(
            text("INSERT INTO closed_date (room_id, closed_date, closure_id) VALUES (:room, :day, :cid)"),
            {"room": room_id, "day": day, "cid": closure_id},
        )
    return closure_id


def add_reservation(room_id: int, check_in: date, nights: int = 1, status: str = "PENDING", *,
                    member_id: int = 2, guests: int = 1, price_per_night: int = 80000,
                    total_price: int | None = None, created_at: datetime | None = None) -> int:
    """예약 하나를 넣고 reservation_id 를 돌려준다. 취소 예약은 canceled_at 도 채운다(③단계 CHECK 대비)."""
    now = datetime.now()
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count,"
                 " total_price, status, price_per_night, canceled_at, created_at)"
                 " VALUES (:mid, :room, :cin, :cout, :guests, :total, :status, :night, :canceled, :created)"
                 " RETURNING reservation_id"),
            {"mid": member_id, "room": room_id, "cin": check_in, "cout": check_in + timedelta(days=nights),
             "guests": guests, "total": price_per_night * nights if total_price is None else total_price,
             "status": status, "night": price_per_night,
             "canceled": None if status in LIVE else now, "created": created_at or now},
        ).scalar_one()
