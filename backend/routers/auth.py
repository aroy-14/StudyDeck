"""
Auth router — registration, login, and current user endpoints.
"""

import uuid
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from data import store
from models.schemas import RegisterRequest, UserResponse, LoginRequest, TokenResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# JWT configuration
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

_security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> str:
    """Decode JWT and return user_id. Raises 401 on any failure."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or user_id not in store.users:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest) -> UserResponse:
    """
    Register a new user account.
    - Email must be unique.
    - Password must be at least 8 characters.
    """
    # Validate password length
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )

    # Check email uniqueness (case-insensitive)
    email_lower = req.email.strip().lower()
    for user in store.users.values():
        if user["email"].lower() == email_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists.",
            )

    # Hash password with bcrypt (use bcrypt directly; passlib 1.7 + bcrypt>=4 has a
    # version-detection incompatibility that raises ValueError on the wrap-bug check)
    import bcrypt as _bcrypt
    password_hash = _bcrypt.hashpw(req.password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

    # Create user record
    user_id = str(uuid.uuid4())
    now = _now_iso()
    user = {
        "id": user_id,
        "email": email_lower,
        "display_name": req.display_name.strip(),
        "password_hash": password_hash,
        "created_at": now,
        "email_verified": True,  # stubbed True for v1
    }
    store.users[user_id] = user

    # Stub: log welcome email (no actual email in v1)
    print(f"[stub] Welcome email sent to {email_lower}")

    return UserResponse(id=user_id, email=email_lower, display_name=user["display_name"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """
    Login with email and password.
    Returns a JWT access token.
    Error messages are intentionally generic — no field disclosure.
    """
    import bcrypt as _bcrypt

    _GENERIC_AUTH_ERROR = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Find user by email (case-insensitive)
    email_lower = req.email.strip().lower()
    found_user = None
    for user in store.users.values():
        if user["email"].lower() == email_lower:
            found_user = user
            break

    if found_user is None:
        raise _GENERIC_AUTH_ERROR

    # Verify password with bcrypt
    try:
        password_matches = _bcrypt.checkpw(
            req.password.encode("utf-8"),
            found_user["password_hash"].encode("utf-8"),
        )
    except Exception:
        raise _GENERIC_AUTH_ERROR

    if not password_matches:
        raise _GENERIC_AUTH_ERROR

    token = _create_access_token(found_user["id"])
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def me(user_id: str = Depends(_get_current_user_id)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    user = store.users[user_id]
    return UserResponse(id=user["id"], email=user["email"], display_name=user["display_name"])
