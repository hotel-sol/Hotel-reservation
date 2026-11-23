"""공통 에러 형식: {"detail": {"code": "...", "message": "..."}}"""
from fastapi import HTTPException


def fail(status: int, code: str, message: str, **extra) -> None:
    raise HTTPException(status, detail={"code": code, "message": message, **extra})
