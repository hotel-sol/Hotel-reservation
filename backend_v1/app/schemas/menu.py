from app.schemas.common import CamelModel


class MenuOut(CamelModel):
    menu_id: int
    parent_id: int | None
    menu_name: str
    menu_url: str | None
    role: str
    sort_order: int
    children: list["MenuOut"] = []
