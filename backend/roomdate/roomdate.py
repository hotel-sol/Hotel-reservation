"""예약 일자(휴무일) 관리 API — 화면 ADM-002, 테이블 closed_date

GET    /admin/closed-dates?month=YYYY-MM[&roomId=]  달의 휴무일 + 날짜별 예약 수
POST   /admin/closed-dates                          휴무일 지정
DELETE /admin/closed-dates/{closedDateId}           휴무 해제
GET    /admin/closed-dates/page                     관리자 화면(roomdate.html)

관리자 확인은 회원 기능(backend/member)의 로그인 세션으로 한다: Depends(require_admin).

다른 앱에 붙일 때: app.include_router(roomdate.router)
혼자 실행: uvicorn roomdate:app --reload  (backend/roomdate 폴더에서, 로그인 · 상단 메뉴 · 뼈대 페이지까지 함께 뜸)
"""
import calendar
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pymysql
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
# ponytail: 팀 메인 앱(패키지 구조)이 생기기 전까지 옆 폴더 모듈을 경로로 불러온다.
sys.path[:0] = [str(HERE.parent / "member"), str(ROOT / "frontend" / "placeholder")]
from member import require_admin  # noqa: E402
from member import router as member_router  # noqa: E402

KST = timezone(timedelta(hours=9))
LIVE_STATUSES = ("PENDING", "APPROVED")  # 객실을 잡고 있는 예약 (대기 + 승인)
DUPLICATE_KEY = 1062


def connect(database: str | None = None):
    # ponytail: 공통 backend/db/connect.py가 채워지면 그쪽으로 바꾼다.
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=database if database is not None else os.getenv("DB_NAME", "hotel"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def fail(status: int, code: str, message: str, **extra):
    raise HTTPException(status, detail={"code": code, "message": message, **extra})


def today_kst() -> date:
    return datetime.now(KST).date()


def count_live_reservations(cur, day: date, room_id: int | None) -> int:
    """그날 밤 묵는 살아 있는 예약 수. 숙박은 [체크인, 체크아웃)이라 체크아웃 날은 세지 않는다."""
    sql = ("SELECT COUNT(*) AS n FROM reservation"
           " WHERE status IN %s AND check_in_date <= %s AND %s < check_out_date")
    params = [LIVE_STATUSES, day, day]
    if room_id is not None:
        sql += " AND room_id = %s"
        params.append(room_id)
    cur.execute(sql, params)
    return cur.fetchone()["n"]


def to_json(row: dict) -> dict:
    return {
        "closedDateId": row["closed_date_id"],
        "roomId": row["room_id"],
        "roomName": row.get("room_name"),
        "closedDate": row["closed_date"].isoformat(),
        "reason": row["reason"],
        "createdAt": row["created_at"].isoformat(),
    }


SELECT_CLOSED = (
    "SELECT c.*, r.room_name FROM closed_date c LEFT JOIN room r ON r.room_id = c.room_id"
)

router = APIRouter(prefix="/admin/closed-dates", tags=["예약 일자 관리"])


@router.get("")
def list_closed_dates(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-12"]),
    room_id: int | None = Query(default=None, alias="roomId"),
    _admin: dict = Depends(require_admin),
    db=Depends(get_db),
):
    """roomId 없음 = 전체 객실: 모든 휴무 + 전체 예약 수.
    roomId 있음 = 그 방: 호텔 전체 휴무 + 그 방 휴무, 그 방 예약 수."""
    year, mon = map(int, month.split("-"))
    first = date(year, mon, 1)
    last = date(year, mon, calendar.monthrange(year, mon)[1])

    closed_sql = SELECT_CLOSED + " WHERE c.closed_date BETWEEN %s AND %s"
    closed_params = [first, last]
    stay_sql = ("SELECT check_in_date, check_out_date FROM reservation"
                " WHERE status IN %s AND check_in_date <= %s AND %s < check_out_date")
    stay_params = [LIVE_STATUSES, last, first]
    if room_id is not None:
        closed_sql += " AND (c.room_id IS NULL OR c.room_id = %s)"
        closed_params.append(room_id)
        stay_sql += " AND room_id = %s"
        stay_params.append(room_id)

    with db.cursor() as cur:
        cur.execute(closed_sql + " ORDER BY c.closed_date, c.room_id", closed_params)
        closed = [to_json(r) for r in cur.fetchall()]
        cur.execute(stay_sql, stay_params)
        stays = cur.fetchall()
        # ① 객실 선택용. ponytail: 객실 API(GET /admin/rooms)가 main에 합쳐지면 화면이 그쪽을 써도 된다.
        cur.execute("SELECT room_id, room_name FROM room ORDER BY room_id")
        rooms = [{"roomId": r["room_id"], "roomName": r["room_name"]} for r in cur.fetchall()]

    counts = {}
    for d in range(1, last.day + 1):
        day = date(year, mon, d)
        n = sum(1 for s in stays if s["check_in_date"] <= day < s["check_out_date"])
        if n:
            counts[day.isoformat()] = n

    return {"month": month, "roomId": room_id, "rooms": rooms,
            "closedDates": closed, "reservationCounts": counts}


@router.get("/page", include_in_schema=False)
def admin_page():
    """ADM-002 화면 본문(①~④). 상단 메뉴(객실 관리 · 예약 관리 · 로그아웃)는 공통 레이아웃 담당이 만든다."""
    return FileResponse(HERE / "roomdate.html")


class ClosedDateIn(BaseModel):
    closed_date: date = Field(alias="closedDate")
    room_id: int | None = Field(default=None, alias="roomId")
    reason: str = Field(min_length=1, max_length=200)


@router.post("", status_code=201)
def create_closed_date(body: ClosedDateIn, _admin: dict = Depends(require_admin), db=Depends(get_db)):
    reason = body.reason.strip()
    if not reason:
        fail(400, "INVALID_INPUT", "휴무 사유를 입력해 주세요.")
    if body.closed_date < today_kst():
        fail(400, "PAST_DATE", "지난 날짜는 휴무로 지정할 수 없습니다.")

    try:
        with db.cursor() as cur:
            if body.room_id is not None:
                cur.execute("SELECT 1 FROM room WHERE room_id = %s", (body.room_id,))
                if cur.fetchone() is None:
                    fail(404, "NOT_FOUND", "없는 객실입니다.")

            # 이미 휴무: 호텔 전체 휴무가 있거나, 같은 방이 이미 휴무.
            # DB UNIQUE(room_id, closed_date)는 room_id가 NULL이면 중복을 막지 못해서 여기서 검사한다.
            # ponytail: 호텔 전체 휴무를 같은 순간에 두 번 넣으면 둘 다 들어갈 수 있다. 문제 되면 FOR UPDATE.
            cur.execute(
                "SELECT 1 FROM closed_date WHERE closed_date = %s AND (room_id IS NULL OR room_id <=> %s)",
                (body.closed_date, body.room_id),
            )
            if cur.fetchone() is not None:
                fail(409, "ALREADY_CLOSED", "이미 휴무로 지정된 날짜입니다.")

            n = count_live_reservations(cur, body.closed_date, body.room_id)
            if n:
                fail(409, "CLOSED_DATE_CONFLICT",
                     f"이 날짜에 예약 {n}건이 있습니다. 먼저 예약을 취소해 주세요.",
                     reservationCount=n)

            cur.execute(
                "INSERT INTO closed_date (room_id, closed_date, reason) VALUES (%s, %s, %s)",
                (body.room_id, body.closed_date, reason),
            )
            cur.execute(SELECT_CLOSED + " WHERE c.closed_date_id = %s", (cur.lastrowid,))
            row = cur.fetchone()
        db.commit()
    except pymysql.IntegrityError as e:
        db.rollback()
        if e.args[0] == DUPLICATE_KEY:
            fail(409, "ALREADY_CLOSED", "이미 휴무로 지정된 날짜입니다.")
        raise
    except Exception:
        db.rollback()
        raise
    return to_json(row)


@router.delete("/{closed_date_id}", status_code=204)
def delete_closed_date(closed_date_id: int, _admin: dict = Depends(require_admin), db=Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("DELETE FROM closed_date WHERE closed_date_id = %s", (closed_date_id,))
        deleted = cur.rowcount
    db.commit()
    if not deleted:
        fail(404, "NOT_FOUND", "없는 휴무일입니다.")


# 혼자 실행용 앱: 이 화면 + 로그인(회원) + 상단 메뉴 + 나머지 메뉴의 뼈대 페이지.
# 팀 메인 앱에서는 router만 붙인다.
app = FastAPI(title="태양의 호텔 · 예약 일자 관리")
app.include_router(router)
app.include_router(member_router)
app.mount("/layout", StaticFiles(directory=ROOT / "frontend" / "layout"), name="layout")
from placeholder import add_placeholders  # noqa: E402

add_placeholders(app)
