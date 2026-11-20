"""
ADM-001 관리자 객실 관리 API (담당 테이블: room)

혼자 테스트하는 방법 (PowerShell, backend/room 폴더에서):
    $env:DB_PASSWORD = "내 MariaDB root 비밀번호"
    python -m uvicorn room:app --reload
    → 브라우저에서 http://127.0.0.1:8000/docs 열기
"""

import os
from typing import Literal, Optional

import pymysql
from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------
# DB 연결 (임시)
# 팀 공용 backend/db/connect.py가 완성되면 이 함수를 그쪽 것으로 바꾼다.
# 비밀번호는 코드에 적지 않고 환경 변수(DB_PASSWORD)에서 읽는다.
# ---------------------------------------------------------------
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "hotel_db"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,  # 결과를 {"컬럼명": 값} 형태로 받기
    )


# 이 파일의 API 묶음. 나중에 팀 메인 앱에서 include_router(router)로 붙인다.
router = APIRouter(prefix="/admin/rooms", tags=["ADM-001 객실 관리"])


# ---------------------------------------------------------------
# 1. 객실 목록 조회  GET /admin/rooms
#    화면 ①: 객실명 검색, 상태(전체/사용 중/비활성) 필터
#    화면 ②: 번호, 사진, 객실명, 종류, 최대 인원, 1박 요금, 상태
# ---------------------------------------------------------------
@router.get("", summary="객실 목록 조회")
def get_rooms(
    keyword: Optional[str] = Query(None, description="객실명 검색어 (일부만 입력해도 됨)"),
    status: Optional[Literal["Y", "N"]] = Query(None, description="Y=사용 중, N=비활성, 비우면 전체"),
):
    # 대표 사진: attach_file에서 이 객실(ROOM)의 첫 번째 파일 경로
    sql = """
        SELECT r.room_id, r.room_name, r.room_type, r.max_guest, r.price,
               r.description, r.view_count, r.is_active, r.created_at,
               (SELECT f.saved_path
                  FROM attach_file f
                 WHERE f.target_type = 'ROOM'
                   AND f.target_id = r.room_id
                 ORDER BY f.file_id
                 LIMIT 1) AS thumbnail_path
          FROM room r
         WHERE 1 = 1
    """
    params = []

    # 조건이 들어온 것만 WHERE에 붙인다. 값은 %s 자리로 넘겨서 SQL 인젝션을 막는다.
    if keyword:
        sql += " AND r.room_name LIKE %s"
        params.append(f"%{keyword}%")
    if status:
        sql += " AND r.is_active = %s"
        params.append(status)

    sql += " ORDER BY r.room_id"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rooms = cur.fetchall()
    finally:
        conn.close()  # 에러가 나도 연결은 꼭 닫기

    return {"count": len(rooms), "rooms": rooms}


# ---------------------------------------------------------------
# 객실 입력값 규칙 (등록·수정에서 같이 사용)
#   * 표시 항목은 필수, 최대 인원 1명 이상, 요금 0원 초과 (화면 ③)
#   글자 수는 DB 컬럼 크기에 맞춘다. 규칙에 어긋나면 FastAPI가 자동으로 422 오류를 돌려준다.
# ---------------------------------------------------------------
INT_MAX = 2_147_483_647  # DB INT 컬럼에 들어갈 수 있는 가장 큰 수


class RoomInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # 앞뒤 공백 자동 제거

    room_name: str = Field(..., min_length=1, max_length=100, description="객실명 (중복 불가)")
    room_type: str = Field(..., min_length=1, max_length=50, description="객실 종류")
    max_guest: int = Field(..., ge=1, le=INT_MAX, description="최대 인원 (1명 이상)")
    price: int = Field(..., gt=0, le=INT_MAX, description="1박 요금 (0원 초과)")
    description: Optional[str] = Field(None, max_length=1000, description="객실 설명 (선택)")


def find_room(cur, room_id: int):
    """room_id로 객실 한 개를 찾는다. 없으면 None."""
    cur.execute(
        """
        SELECT room_id, room_name, room_type, max_guest, price,
               description, view_count, is_active, created_at
          FROM room
         WHERE room_id = %s
        """,
        (room_id,),
    )
    return cur.fetchone()


def is_duplicate_error(e: pymysql.err.IntegrityError) -> bool:
    """DB가 UNIQUE 위반(같은 객실명)으로 거절했는지 확인. 1062 = 중복 키 오류 번호."""
    return e.args[0] == 1062


# ---------------------------------------------------------------
# 2. 객실 등록  POST /admin/rooms
#    성공하면 201과 함께 새로 만든 객실 정보를 돌려준다.
#    같은 객실명이 있으면 409 오류.
# ---------------------------------------------------------------
@router.post("", status_code=201, summary="객실 등록")
def create_room(room: RoomInput):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1) 객실명 중복 확인 (비활성 객실 이름도 중복으로 본다)
            cur.execute("SELECT room_id FROM room WHERE room_name = %s", (room.room_name,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail=f"이미 있는 객실명입니다: {room.room_name}")

            # 2) 저장 (view_count, is_active, created_at은 DB 기본값 사용)
            try:
                cur.execute(
                    """
                    INSERT INTO room (room_name, room_type, max_guest, price, description)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (room.room_name, room.room_type, room.max_guest, room.price, room.description),
                )
            except pymysql.err.IntegrityError as e:
                # 1)과 2) 사이에 다른 사람이 같은 이름을 먼저 저장한 경우 대비
                if is_duplicate_error(e):
                    raise HTTPException(status_code=409, detail=f"이미 있는 객실명입니다: {room.room_name}")
                raise
            conn.commit()  # commit을 해야 DB에 실제로 저장된다

            # 3) 방금 저장한 객실을 다시 읽어서 돌려주기
            return find_room(cur, cur.lastrowid)
    finally:
        conn.close()


# ---------------------------------------------------------------
# 3. 객실 수정  PUT /admin/rooms/{room_id}
#    화면 ③ 입력 칸의 내용 전체를 받아서 바꾼다.
#    (설명을 비워서 보내면 설명도 비워진다. 조회수·사용 여부·등록 시각은 그대로.)
#    없는 객실이면 404, 다른 객실과 이름이 같으면 409.
# ---------------------------------------------------------------
@router.put("/{room_id}", summary="객실 수정")
def update_room(room_id: int, room: RoomInput):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1) 수정할 객실이 있는지 확인
            if not find_room(cur, room_id):
                raise HTTPException(status_code=404, detail=f"객실을 찾을 수 없습니다: {room_id}번")

            # 2) 객실명 중복 확인 (자기 자신은 빼고 비교)
            cur.execute(
                "SELECT room_id FROM room WHERE room_name = %s AND room_id <> %s",
                (room.room_name, room_id),
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail=f"이미 있는 객실명입니다: {room.room_name}")

            # 3) 저장
            try:
                cur.execute(
                    """
                    UPDATE room
                       SET room_name = %s, room_type = %s, max_guest = %s,
                           price = %s, description = %s
                     WHERE room_id = %s
                    """,
                    (room.room_name, room.room_type, room.max_guest,
                     room.price, room.description, room_id),
                )
            except pymysql.err.IntegrityError as e:
                if is_duplicate_error(e):
                    raise HTTPException(status_code=409, detail=f"이미 있는 객실명입니다: {room.room_name}")
                raise
            conn.commit()

            # 4) 바뀐 객실 정보를 다시 읽어서 돌려주기
            return find_room(cur, room_id)
    finally:
        conn.close()


# ---------------------------------------------------------------
# 4. 객실 사용/중지  PATCH /admin/rooms/{room_id}/status
#    삭제 대신 is_active만 바꾼다. (Y = 사용 중, N = 비활성)
#    비활성 객실은 손님 추천 화면에서 빠지지만, 이미 잡힌 예약은 그대로 둔다.
#    이미 같은 상태여도 오류 없이 200을 돌려준다.
# ---------------------------------------------------------------
class RoomStatusInput(BaseModel):
    is_active: Literal["Y", "N"] = Field(..., description="Y=사용 중, N=비활성")


@router.patch("/{room_id}/status", summary="객실 사용/중지 변경")
def change_room_status(room_id: int, body: RoomStatusInput):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if not find_room(cur, room_id):
                raise HTTPException(status_code=404, detail=f"객실을 찾을 수 없습니다: {room_id}번")

            cur.execute(
                "UPDATE room SET is_active = %s WHERE room_id = %s",
                (body.is_active, room_id),
            )
            conn.commit()

            return find_room(cur, room_id)
    finally:
        conn.close()


# ---------------------------------------------------------------
# 혼자 테스트할 때만 쓰는 앱 (uvicorn room:app)
# ---------------------------------------------------------------
app = FastAPI(title="호텔 예약 - 객실 관리(ADM-001)")
app.include_router(router)
