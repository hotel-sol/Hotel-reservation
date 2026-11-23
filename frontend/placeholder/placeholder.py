"""아직 없는 메뉴 화면의 임시 뼈대 페이지("준비 중").

메인 앱에서 다른 라우터를 모두 붙인 뒤 **마지막에** 한 줄:
    from placeholder import add_placeholders
    add_placeholders(app)
이미 진짜 화면이 붙은 주소는 건너뛰므로, 각 담당 화면이 합쳐지면 자동으로 그 화면이 나온다.
모든 화면이 생기면 이 폴더를 지운다.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

PAGE = Path(__file__).with_name("placeholder.html")

# 상단 메뉴(frontend/layout/layout.js)의 MENUS와 같은 주소
PAGES = (
    "/admin/rooms/page",          # ADM-001 객실 관리
    "/admin/closed-dates/page",   # ADM-002 예약 일자 관리
    "/admin/reservations/page",   # ADM-003 예약 관리
    "/rooms/page",                # ROOM-001 객실 추천
    "/reservations/page",         # 내 예약
)


def add_placeholders(app: FastAPI) -> list[str]:
    """아직 GET 화면이 없는 주소에만 뼈대 페이지를 붙이고, 붙인 주소 목록을 돌려준다."""
    taken = {r.path for r in app.routes if "GET" in getattr(r, "methods", set())}
    added = [p for p in PAGES if p not in taken]
    for path in added:
        app.add_api_route(path, lambda: FileResponse(PAGE), methods=["GET"], include_in_schema=False)
    return added


if __name__ == "__main__":
    demo = FastAPI()
    demo.add_api_route("/rooms/page", lambda: "진짜 화면", methods=["GET"])
    added = add_placeholders(demo)
    assert "/rooms/page" not in added and "/admin/rooms/page" in added, added
    assert len(added) == len(PAGES) - 1
    print("ok", added)
