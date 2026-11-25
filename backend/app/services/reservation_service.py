"""예약 저장(POST /api/reservations)과 요금 견적(GET /api/rooms/{id}/quote)이 같이 쓰는 확인 · 계산 (Step 2 4C).

두 API가 이 함수들만 쓰게 해서, 견적에서 본 금액과 실제 저장되는 금액이 어긋나지 않게 한다.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dates import today_kst
from app.core.exceptions import fail
from app.models import Member, Reservation, Room
from app.models.reservation import PENDING

# 한 번에 예약할 수 있는 범위 (팀 협의 후 조정). 화면 달력(StayCalendar.tsx 의 MAX_NIGHTS)도 같은 값.
# 상한이 없으면 수십 년짜리 예약으로 방을 막거나, 총액이 DB INT 한도를 넘어 저장이 실패한다.
MAX_NIGHTS = 6
BOOKING_WINDOW_DAYS = 30  # 체크인은 오늘부터 이 날수 안
# 회원 한 명이 동시에 가질 수 있는 승인 대기 예약 수 (#68). 대기 예약도 방을 잡으므로,
# 상한이 없으면 계정 하나로 모든 방의 날짜를 막을 수 있다.
MAX_PENDING_PER_MEMBER = 3


def check_pending_limit(db: Session, member_id: int) -> None:
    """아직 끝나지 않은(체크아웃이 오늘 뒤) 승인 대기 예약이 상한이면 409 TOO_MANY_PENDING.

    회원 행을 잠가서 같은 회원의 동시 요청(서로 다른 방이어도)을 한 줄로 세운다.
    잠금 순서는 회원 → 객실 (예약 저장에서만 회원 행을 잠근다).
    """
    db.execute(select(Member.member_id).where(Member.member_id == member_id).with_for_update())
    pending = db.scalar(
        select(func.count()).select_from(Reservation).where(
            Reservation.member_id == member_id,
            Reservation.status == PENDING,
            Reservation.check_out_date > today_kst(),  # 이미 끝난 대기 예약은 방을 잡지 않으므로 세지 않음
        )
    )
    if pending >= MAX_PENDING_PER_MEMBER:
        fail(409, "TOO_MANY_PENDING",
             f"승인 대기 중인 예약은 최대 {MAX_PENDING_PER_MEMBER}건까지 할 수 있습니다. "
             "승인되거나 취소된 뒤 다시 예약해 주세요.")


def get_bookable_room(db: Session, room_id: int, lock: bool = False) -> Room:
    """판매 중인 객실. 없거나 판매 안 하면 404. lock=True 면 객실 행을 잠근다(예약 저장용)."""
    room = db.get(Room, room_id, with_for_update=lock)
    if room is None or room.is_active != "Y":
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    return room


def check_stay(room: Room, check_in: date, check_out: date, guests: int) -> int:
    """날짜 순서 · 인원 · 지난 날짜 · 예약 가능 범위를 확인하고 박수를 돌려준다."""
    if check_out <= check_in:
        fail(400, "INVALID_DATES", "체크아웃은 체크인 다음 날부터 선택할 수 있습니다.")
    if guests > room.max_guest:
        fail(400, "TOO_MANY_GUESTS", f"최대 {room.max_guest}명까지 예약할 수 있습니다.")
    today = today_kst()
    if check_in < today:
        fail(400, "PAST_DATE", "지난 날짜는 예약할 수 없습니다.")
    if check_in > today + timedelta(days=BOOKING_WINDOW_DAYS):
        fail(400, "TOO_FAR_DATE", f"체크인은 오늘부터 {BOOKING_WINDOW_DAYS}일 안의 날짜만 예약할 수 있습니다.")
    nights = (check_out - check_in).days
    if nights > MAX_NIGHTS:
        fail(400, "TOO_LONG_STAY", f"한 번에 최대 {MAX_NIGHTS}박까지 예약할 수 있습니다.")
    return nights


def night_price(room: Room) -> int:
    """1박 요금. 예약에 price_per_night 로 저장하고 견적에도 보여 준다 (4-A3)."""
    return room.price


def total_price(room: Room, nights: int) -> int:
    """총액 = 1박 요금 × 박수

    요금 계산은 여기(night_price · total_price) 한 곳에만 둔다 (#60 문제 ④). 예약 저장 · 견적(quote)이 같이 쓴다.
    등급 · 전망 · 성수기 · 회원가 같은 규칙이 생기면 이 두 함수 안에서 순서 · 반올림을 정하고,
    다른 파일에서 room.price × 박수를 직접 계산하지 않는다.
    """
    return night_price(room) * nights
