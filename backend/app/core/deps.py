import time
from typing import Optional, Dict, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import UserModel
from app.core.security import decode_access_token

security_bearer = HTTPBearer(auto_error=False)

# In-memory sliding window rate limiter for login attempts
# key -> list of timestamp floats
_FAILED_LOGIN_ATTEMPTS: Dict[str, List[float]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 60.0

def check_login_rate_limit(key: str):
    """
    Checks if a given IP or identifier has exceeded the maximum allowed failed attempts.
    Raises HTTP 429 Too Many Requests if rate limit exceeded.
    """
    now = time.time()
    attempts = _FAILED_LOGIN_ATTEMPTS.get(key, [])
    # Filter attempts within the lockout window
    valid_attempts = [t for t in attempts if now - t < LOCKOUT_WINDOW_SECONDS]
    _FAILED_LOGIN_ATTEMPTS[key] = valid_attempts

    if len(valid_attempts) >= MAX_FAILED_ATTEMPTS:
        retry_after = int(LOCKOUT_WINDOW_SECONDS - (now - valid_attempts[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please try again in {retry_after} seconds."
        )

def record_failed_login(key: str):
    """Records a failed attempt for the rate limiter."""
    now = time.time()
    attempts = _FAILED_LOGIN_ATTEMPTS.get(key, [])
    attempts.append(now)
    _FAILED_LOGIN_ATTEMPTS[key] = attempts

def clear_failed_logins(key: str):
    """Clears failed login attempts after successful authentication."""
    if key in _FAILED_LOGIN_ATTEMPTS:
        del _FAILED_LOGIN_ATTEMPTS[key]

def extract_token_from_request(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> Optional[str]:
    """
    Extracts JWT from Authorization header Bearer token, or from clippilot_token cookie,
    or from token query parameter (vital for direct downloads and media streaming).
    """
    if auth_header and auth_header.credentials:
        return auth_header.credentials
    # Fallback to query parameter (e.g. ?token=...)
    query_token = request.query_params.get("token")
    if query_token:
        return query_token
    # Fallback to cookie
    cookie_token = request.cookies.get("clippilot_token")
    if cookie_token:
        return cookie_token
    return None

async def get_current_user(
    token: Optional[str] = Depends(extract_token_from_request),
    db: Session = Depends(get_db)
) -> UserModel:
    """
    Authoritative dependency to get authenticated UserModel.
    Returns 401 if missing, invalid, or expired.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user

async def get_current_user_optional(
    token: Optional[str] = Depends(extract_token_from_request),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """
    Optional dependency. Returns UserModel if valid token provided, otherwise None.
    Does not raise 401 if token is omitted.
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if not payload or not payload.get("sub"):
            return None
        user = db.query(UserModel).filter(UserModel.id == payload.get("sub")).first()
        if user and user.is_active:
            return user
    except Exception:
        pass
    return None
