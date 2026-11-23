"""비밀번호 해시 · 세션 토큰.

비밀번호: 참고 저장소(member.py)와 같은 "scrypt$salt$hash" 형식이라 기존 회원 데이터와 호환된다.
세션: member_id 를 서명한 쿠키 (itsdangerous). DB 세션 테이블 없이 동작.
"""
import hashlib
import hmac
import secrets

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), hash_hex)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="hotel-session")


def create_session_token(member_id: int) -> str:
    return _serializer().dumps({"mid": member_id})


def read_session_token(token: str) -> int | None:
    try:
        data = _serializer().loads(token, max_age=get_settings().session_seconds)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("mid")
