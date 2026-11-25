"""비밀번호 해시 · 세션 토큰.

비밀번호: 참고 저장소(member.py)와 같은 "scrypt$salt$hash" 형식이라 기존 회원 데이터와 호환된다.
세션: member_id + 비밀번호 표식을 서명한 쿠키 (itsdangerous). DB 세션 테이블 없이 동작.
     비밀번호를 바꾸거나 탈퇴하면 표식이 달라져서 예전 쿠키(다른 기기 로그인)는 모두 무효가 된다.
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


def password_tag(stored_password: str) -> str:
    """저장된 비밀번호 해시의 짧은 지문. 비밀번호가 바뀌면 달라진다."""
    return hashlib.sha256(stored_password.encode()).hexdigest()[:12]


def create_session_token(member_id: int, stored_password: str) -> str:
    return _serializer().dumps({"mid": member_id, "pw": password_tag(stored_password)})


def read_session_token(token: str) -> tuple[int, str] | None:
    """서명 · 만료가 맞으면 (회원번호, 비밀번호 표식)."""
    try:
        data = _serializer().loads(token, max_age=get_settings().session_seconds)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict) or "mid" not in data or "pw" not in data:
        return None
    return data["mid"], data["pw"]


# ---------- 기기 기억(로그인 잠금용, #67-3) ----------
# 로그인에 성공한 기기에 "이 기기는 N번 회원이 쓴 적 있음" 표를 서명해서 준다.
# 남이 내 아이디로 일부러 틀려 잠가도, 이 표가 있는 내 기기는 따로 센다(OWASP device cookie).
DEVICE_SECONDS = 365 * 24 * 3600


def _device_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="hotel-device")


def create_device_token(member_id: int) -> str:
    return _device_serializer().dumps({"mid": member_id, "d": secrets.token_hex(8)})


def read_device_token(token: str) -> tuple[int, str] | None:
    """서명 · 만료가 맞으면 (회원번호, 기기 번호)."""
    try:
        data = _device_serializer().loads(token, max_age=DEVICE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("mid"), int) or not isinstance(data.get("d"), str):
        return None
    return data["mid"], data["d"][:16]
