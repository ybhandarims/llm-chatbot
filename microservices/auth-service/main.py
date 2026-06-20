from datetime import datetime, timedelta
import json
import logging
import os
import uuid
from typing import Dict, List, Optional, Tuple

import redis
from fastapi import Depends, FastAPI, Header, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))
REFRESH_TOKEN_TTL_SECONDS = int(os.getenv("REFRESH_TOKEN_TTL_SECONDS", "604800"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def to_json(value) -> str:
    return json.dumps(value)


def from_json(value: Optional[str], default=None):
    if value is None:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def user_key(username: str) -> str:
    return f"user:{normalize_username(username)}"


def session_key(token: str) -> str:
    return f"session:{token}"


def refresh_key(token: str) -> str:
    return f"refresh:{token}"


def role_key(role: str) -> str:
    return f"role:{role}:permissions"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    roles: List[str]


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class UserCreateRequest(BaseModel):
    username: str
    password: str
    roles: List[str]


class UserResponse(BaseModel):
    username: str
    roles: List[str]
    created_at: str


class PermissionUpdateRequest(BaseModel):
    permissions: List[str]


class AuthorizeRequest(BaseModel):
    permission: str


@app.on_event("startup")
def startup_event():
    try:
        redis_client.ping()
    except redis.RedisError as exc:
        logger.warning("Redis connectivity issue on startup: %s", exc)

    ensure_role(
        "admin",
        [
            "auth:manage",
            "users:manage",
            "roles:manage",
            "chat:send",
            "settings:read",
            "settings:write",
            "conversations:read",
            "messages:read",
            "messages:write",
        ],
    )
    ensure_role(
        "user", ["chat:send", "conversations:read", "messages:write", "settings:read"]
    )
    ensure_default_admin()


def ensure_role(role: str, permissions: List[str]):
    key = role_key(role)
    if not redis_client.exists(key):
        redis_client.sadd(key, *permissions)
        logger.info("Seeded RBAC role %s with %s permissions", role, permissions)


def ensure_default_admin():
    if not redis_client.exists(user_key(ADMIN_USERNAME)):
        create_user(ADMIN_USERNAME, ADMIN_PASSWORD, ["admin"])
        logger.info("Seeded default admin user %s", ADMIN_USERNAME)


def create_user(username: str, password: str, roles: List[str]):
    if not username or not password:
        raise ValueError("username and password are required")
    key = user_key(username)
    if redis_client.exists(key):
        raise ValueError("user already exists")
    redis_client.hset(
        key,
        mapping={
            "password_hash": hash_password(password),
            "roles": to_json(roles),
            "created_at": datetime.utcnow().isoformat() + "Z",
        },
    )


def get_user(username: str) -> Optional[Dict[str, str]]:
    key = user_key(username)
    data = redis_client.hgetall(key)
    if not data:
        return None
    return {
        "username": normalize_username(username),
        "password_hash": data.get("password_hash", ""),
        "roles": from_json(data.get("roles"), []),
        "created_at": data.get("created_at", ""),
    }


def create_session(username: str) -> Tuple[str, str]:
    access_token = str(uuid.uuid4())
    refresh_token = str(uuid.uuid4())
    access_key = session_key(access_token)
    refresh_key_value = refresh_key(refresh_token)

    session_data = {
        "username": normalize_username(username),
        "refresh_token": refresh_token,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    redis_client.hset(access_key, mapping=session_data)
    redis_client.expire(access_key, TOKEN_TTL_SECONDS)

    refresh_data = {
        "username": normalize_username(username),
        "access_token": access_token,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    redis_client.hset(refresh_key_value, mapping=refresh_data)
    redis_client.expire(refresh_key_value, REFRESH_TOKEN_TTL_SECONDS)

    return access_token, refresh_token


def get_session(token: str) -> Optional[Dict[str, str]]:
    key = session_key(token)
    data = redis_client.hgetall(key)
    if not data:
        return None
    return data


def get_refresh_session(refresh_token: str) -> Optional[Dict[str, str]]:
    key = refresh_key(refresh_token)
    data = redis_client.hgetall(key)
    if not data:
        return None
    return data


def invalidate_session(access_token: str) -> None:
    session = get_session(access_token)
    if not session:
        return
    refresh_token = session.get("refresh_token")
    redis_client.delete(session_key(access_token))
    if refresh_token:
        redis_client.delete(refresh_key(refresh_token))


def invalidate_refresh_token(refresh_token: str) -> None:
    refresh = get_refresh_session(refresh_token)
    if not refresh:
        return
    access_token = refresh.get("access_token")
    redis_client.delete(refresh_key(refresh_token))
    if access_token:
        redis_client.delete(session_key(access_token))


def refresh_access_token(refresh_token: str) -> Optional[Tuple[str, str]]:
    refresh = get_refresh_session(refresh_token)
    if not refresh:
        return None
    username = refresh.get("username")
    invalidate_refresh_token(refresh_token)
    return create_session(username)


def get_role_permissions(role: str) -> List[str]:
    return sorted(redis_client.smembers(role_key(role)))


def user_has_permission(username: str, permission: str) -> bool:
    user = get_user(username)
    if not user:
        return False
    for role in user["roles"]:
        if permission in get_role_permissions(role):
            return True
    return False


def get_current_username(authorization: Optional[str] = Header(None)) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = authorization.split(" ", 1)[1].strip()
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return session["username"]


def require_admin(username: str = Depends(get_current_username)) -> str:
    if not user_has_permission(username, "users:manage"):
        raise HTTPException(status_code=403, detail="Admin permission required")
    return username


@app.get("/health")
def health():
    try:
        redis_client.ping()
        return {"status": "ok", "service": "auth"}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}")


@app.post("/api/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = get_user(payload.username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token, refresh_token = create_session(payload.username)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=TOKEN_TTL_SECONDS,
        refresh_expires_in=REFRESH_TOKEN_TTL_SECONDS,
        roles=user["roles"],
    )


@app.post("/api/users", response_model=UserResponse)
def create_user_endpoint(
    payload: UserCreateRequest, admin_username: str = Depends(require_admin)
):
    try:
        create_user(payload.username, payload.password, payload.roles)
        user = get_user(payload.username)
        return UserResponse(
            username=user["username"],
            roles=user["roles"],
            created_at=user["created_at"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/users/{username}", response_model=UserResponse)
def get_user_endpoint(username: str, admin_username: str = Depends(require_admin)):
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        username=user["username"],
        roles=user["roles"],
        created_at=user["created_at"],
    )


@app.get("/api/roles/{role}")
def get_role(role: str, admin_username: str = Depends(require_admin)):
    return {"role": role, "permissions": get_role_permissions(role)}


@app.post("/api/roles/{role}/permissions")
def add_role_permissions(
    role: str,
    payload: PermissionUpdateRequest,
    admin_username: str = Depends(require_admin),
):
    key = role_key(role)
    redis_client.sadd(key, *payload.permissions)
    return {"role": role, "permissions": get_role_permissions(role)}


@app.post("/api/refresh", response_model=LoginResponse)
def refresh_token_endpoint(payload: RefreshRequest):
    updated = refresh_access_token(payload.refresh_token)
    if not updated:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    access_token, refresh_token = updated
    session = get_session(access_token)
    if not session:
        raise HTTPException(
            status_code=500, detail="Failed to create refreshed session"
        )
    user = get_user(session["username"])
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=TOKEN_TTL_SECONDS,
        refresh_expires_in=REFRESH_TOKEN_TTL_SECONDS,
        roles=user["roles"] if user else [],
    )


@app.post("/api/logout")
def logout(
    payload: Optional[LogoutRequest] = None,
    authorization: Optional[str] = Header(None),
):
    access_token = None
    if authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1].strip()

    if access_token:
        invalidate_session(access_token)

    if payload and payload.refresh_token:
        invalidate_refresh_token(payload.refresh_token)

    if not access_token and not (payload and payload.refresh_token):
        raise HTTPException(
            status_code=400, detail="Authorization or refresh_token required"
        )

    return {"detail": "Logged out"}


@app.post("/api/authorize")
def authorize(
    payload: AuthorizeRequest,
    authorization: Optional[str] = Header(None),
):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = authorization.split(" ", 1)[1].strip()
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    username = session["username"]
    allowed = user_has_permission(username, payload.permission)
    return {"username": username, "permission": payload.permission, "allowed": allowed}
