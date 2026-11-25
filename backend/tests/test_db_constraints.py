"""#60 ③단계 강화: DB 제약이 실제로 막는지. 코드가 실수해도 DB가 마지막에 막는다."""
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import engine
from tests import helpers
from tests.test_closed_dates import D1

pytestmark = pytest.mark.usefixtures("seeded_db")


def sql(statement, **params):
    with engine.begin() as conn:
        return conn.execute(text(statement), params)


def sqlstate(e: IntegrityError) -> str:
    return e.orig.sqlstate


def test_overlapping_live_reservations_are_rejected_by_db():
    """4-A1 EXCLUDE: 같은 방 · 겹치는 날짜의 살아 있는 예약 2건은 저장 불가(23P01)."""
    helpers.add_reservation(1, D1, 2)
    with pytest.raises(IntegrityError) as e:
        helpers.add_reservation(1, D1 + timedelta(days=1), 1, member_id=1)
    assert sqlstate(e.value) == "23P01"
    helpers.add_reservation(1, D1 + timedelta(days=2), 1, member_id=1)  # 체크아웃 날 체크인은 가능
    helpers.add_reservation(2, D1, 2, member_id=1)                       # 다른 방은 가능
    helpers.add_reservation(1, D1, 2, status="CANCELED", member_id=1)    # 취소 예약은 검사에서 빠짐


def test_canceled_needs_canceled_at_and_live_must_not_have_it():
    """4-A4 CHECK: CANCELED ↔ canceled_at 짝."""
    rid = helpers.add_reservation(1, D1, 1)
    with pytest.raises(IntegrityError) as e:
        sql("UPDATE reservation SET status = 'CANCELED' WHERE reservation_id = :id", id=rid)
    assert sqlstate(e.value) == "23514"
    with pytest.raises(IntegrityError):
        sql("UPDATE reservation SET canceled_at = now() WHERE reservation_id = :id", id=rid)  # 대기인데 취소 시각


def test_price_per_night_and_closure_id_are_required():
    with pytest.raises(IntegrityError) as e:
        sql("INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count, total_price)"
            " VALUES (2, 1, :d, :d2, 1, 80000)", d=D1, d2=D1 + timedelta(days=1))
    assert sqlstate(e.value) == "23502"  # NOT NULL
    with pytest.raises(IntegrityError) as e:
        sql("INSERT INTO closed_date (room_id, closed_date) VALUES (NULL, :d)", d=D1)
    assert sqlstate(e.value) == "23502"


def test_closed_date_reason_column_removed_and_grade_base_guest():
    cols = sql("SELECT column_name FROM information_schema.columns"
               " WHERE table_schema = current_schema() AND table_name = 'closed_date'").scalars().all()
    assert "reason" not in cols and "closure_id" in cols
    guests = dict(sql("SELECT grade_code, base_guest FROM room_grade").all())
    assert guests == {"S": 4, "A": 2, "B": 2, "C": 2}


def test_member_phone_is_required_by_db():
    """전화번호 필수(#108): 코드를 거치지 않고 넣어도 phone 이 비면 저장 불가(23502 NOT NULL)."""
    with pytest.raises(IntegrityError) as e:
        sql("INSERT INTO member (login_id, password, name) VALUES ('nophone', 'x', '손님')")
    assert sqlstate(e.value) == "23502"
