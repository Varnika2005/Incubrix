from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import UserModel
from app.schemas.auth import UserCreate, UserLogin, UserResponse, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REMEMBER_ME_EXPIRE_MINUTES
)
from app.core.deps import (
    get_current_user,
    check_login_rate_limit,
    record_failed_login,
    clear_failed_logins
)

router = APIRouter()

@router.post("/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: UserCreate,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Register a new user account with validated credentials and hashed password.
    """
    normalized_email = payload.email.strip().lower()
    
    # Check for duplicate email
    existing_user = db.query(UserModel).filter(UserModel.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please sign in instead."
        )

    # Hash password securely with bcrypt
    hashed_pw = hash_password(payload.password)

    user = UserModel(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        hashed_password=hashed_pw,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create session token
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=expires_delta
    )

    # Set secure cookie
    response.set_cookie(
        key="clippilot_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production HTTPS
        max_age=int(expires_delta.total_seconds())
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/auth/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with email and password, returning JWT token and setting session cookie.
    Enforces rate limiting to prevent brute-force attacks.
    """
    normalized_email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{normalized_email}"

    # 1. Rate limiting check
    check_login_rate_limit(rate_limit_key)

    # 2. Query user
    user = db.query(UserModel).filter(UserModel.email == normalized_email).first()
    
    # 3. Verify password (constant-time check even if user doesn't exist to mitigate timing attacks)
    is_valid = False
    if user and user.is_active:
        is_valid = verify_password(payload.password, user.hashed_password)
    else:
        # Dummy verification to balance execution time
        verify_password("dummy_password_for_timing_safety", "$2b$12$e9wG.d.Oqg4lE2i.p40qeeGkO8Q6xW7x2kYwP6T5wJ9pM7.9tNeqy")

    if not is_valid or not user:
        record_failed_login(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 4. Authentication succeeded: clear rate limit counter
    clear_failed_logins(rate_limit_key)

    # 5. Token expiration depending on remember_me
    expire_minutes = REMEMBER_ME_EXPIRE_MINUTES if payload.remember_me else ACCESS_TOKEN_EXPIRE_MINUTES
    expires_delta = timedelta(minutes=expire_minutes)
    token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=expires_delta
    )

    response.set_cookie(
        key="clippilot_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=int(expires_delta.total_seconds())
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieve authenticated user profile.
    """
    return UserResponse.model_validate(current_user)

@router.post("/auth/logout")
def logout(response: Response):
    """
    Sign out user and clear authentication cookie.
    """
    response.delete_cookie(
        key="clippilot_token",
        httponly=True,
        samesite="lax",
        secure=False
    )
    return {"status": "logged_out", "message": "Successfully signed out"}
