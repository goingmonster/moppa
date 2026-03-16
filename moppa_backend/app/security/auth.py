import base64
import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.config import settings


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _json_dumps(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    rounds = 120_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_password: str) -> bool:
    try:
        algorithm, rounds_text, salt_hex, digest_hex = encoded_password.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        rounds = int(rounds_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(computed, expected)


def _build_token(payload: dict[str, object]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _b64url_encode(_json_dumps(header).encode("utf-8"))
    payload_segment = _b64url_encode(_json_dumps(payload).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(settings.auth_jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def _decode_token(token: str) -> dict[str, object]:
    segments = token.split(".")
    if len(segments) != 3:
        raise ValueError("invalid token")
    header_segment, payload_segment, signature_segment = segments
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(settings.auth_jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("invalid token signature")
    payload_raw = _b64url_decode(payload_segment)
    payload_obj = json.loads(payload_raw.decode("utf-8"))
    if not isinstance(payload_obj, dict):
        raise ValueError("invalid token payload")
    exp = payload_obj.get("exp")
    if not isinstance(exp, int):
        raise ValueError("invalid token exp")
    if exp <= int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("token expired")
    return payload_obj


def create_access_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.auth_access_token_expire_minutes)
    payload: dict[str, object] = {
        "iss": settings.auth_jwt_issuer,
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(uuid4()),
    }
    return _build_token(payload)


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.auth_refresh_token_expire_days)
    payload: dict[str, object] = {
        "iss": settings.auth_jwt_issuer,
        "sub": user_id,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(uuid4()),
    }
    return _build_token(payload), expires_at


def decode_access_token(token: str) -> dict[str, object]:
    payload = _decode_token(token)
    token_type = payload.get("type")
    if token_type != "access":
        raise ValueError("invalid access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, object]:
    payload = _decode_token(token)
    token_type = payload.get("type")
    if token_type != "refresh":
        raise ValueError("invalid refresh token")
    return payload


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_integration_api_token(token: str) -> bool:
    configured = settings.integration_api_token.strip()
    if not configured:
        return False
    return hmac.compare_digest(token, configured)
