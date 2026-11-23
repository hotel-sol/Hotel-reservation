"""API 응답 공통: JSON 키는 camelCase (프론트 TypeScript 와 맞춤)."""
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class Page(CamelModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class Message(CamelModel):
    message: str
