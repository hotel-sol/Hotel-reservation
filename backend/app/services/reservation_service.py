"""예약 저장(POST /api/reservations)과 요금 견적(GET /api/rooms/{id}/quote)이 같이 쓰는 확인 · 계산 (Step 2 4C).

두 API가 이 함수들만 쓰게 해서, 견적에서 본 금액과 실제 저장되는 금액이 어긋나지 않게 한다.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.core.dates import today_kst
from app.core.exceptions import fail
from app.models import Room


def get_bookable_room(db: Session, room_id: int, lock: bool = False) -> Room:
    """판매 중인 객실. 없거나 판매 안 하면 404. lock=True 면 객실 행을 잠근다(예약 저장용)."""
    room = db.get(Room, room_id, with_for_update=lock)
    if room is None or room.is_active != "Y":
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    return room


def check_stay(room: Room, check_in: date, check_out: date, guests: int) -> int:
    """날짜 순서 · 인원 · 지난 날짜를 확인하고 박수를 돌려준다."""
    if check_out <= check_in:
        fail(400, "INVALID_DATES", "체크아웃은 체크인 다음 날부터 선택할 수 있습니다.")
    if guests > room.max_guest:
        fail(400, "TOO_MANY_GUESTS", f"최대 {room.max_guest}명까지 예약할 수 있습니다.")
    if check_in < today_kst():
        fail(400, "PAST_DATE", "지난 날짜는 예약할 수 없습니다.")
    return (check_out - check_in).days


def total_price(room: Room, nights: int) -> int:
    """총액 = 1박 요금 × 박수"""
    return room.price * nights
