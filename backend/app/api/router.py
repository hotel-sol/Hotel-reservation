from fastapi import APIRouter

from app.api.routes import files, health, members, menus, reservations, room_grades, rooms
from app.api.routes.admin import closed_dates as admin_closed_dates
from app.api.routes.admin import reservations as admin_reservations
from app.api.routes.admin import rooms as admin_rooms

api_router = APIRouter()
for r in (
    health.router,
    members.router,
    menus.router,
    rooms.router,
    room_grades.router,
    reservations.router,
    files.router,
    admin_rooms.router,
    admin_closed_dates.router,
    admin_closed_dates.closures_router,
    admin_reservations.router,
):
    api_router.include_router(r)
