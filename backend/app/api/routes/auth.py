import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import resend
from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.health import PasswordResetToken, User
from app.schemas.health import (
    AuthLogin,
    AuthRegister,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserOut,
)
from app.security import create_access_token, hash_password, verify_password
router = APIRouter(prefix="/api/auth", tags=["authentication"])
SESSION_COOKIE = "carecompass_session"


def _session_cookie_options() -> dict[str, bool | str]:
    return {
        "httponly": True,
        "secure": True,
        "samesite": "none",
        "path": "/",
    }


def _require_auth_configuration() -> None:
    if len(settings.auth_secret_key.encode("utf-8")) < 32:
        raise HTTPException(status_code=503, detail="Authentication is not configured.")


def _set_session_cookie(response: Response, user_id: int) -> None:
    try:
        token = create_access_token(user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Authentication is not configured.") from exc
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=settings.auth_token_expire_minutes * 60,
        **_session_cookie_options(),
    )


def _user_response(user: User) -> dict:
    return {"user": UserOut.model_validate(user, from_attributes=True)}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegister, response: Response):
    _require_auth_configuration()
    normalized_email = payload.email.strip().casefold()
    if not normalized_email:
        raise HTTPException(status_code=422, detail="A valid email is required.")
    with SessionLocal() as db:
        user = User(
            name=payload.name.strip(),
            email=normalized_email,
            phone=payload.phone,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
        db.refresh(user)
        result = _user_response(user)
        _set_session_cookie(response, user.id)
        return result


@router.post("/login")
def login(payload: AuthLogin, response: Response):
    _require_auth_configuration()
    normalized_email = payload.email.strip().casefold()
    with SessionLocal() as db:
        user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
        if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Email or password is incorrect.")
        result = _user_response(user)
        _set_session_cookie(response, user.id)
        return result


@router.get("/me")
def current_session(request: Request):
    user_id = getattr(request.state, "authenticated_user_id", None)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return _user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE,
        **_session_cookie_options(),
    )

def send_reset_email(email: str, reset_url: str) -> None:
    resend.api_key = settings.resend_api_key

    resend.Emails.send({
        "from": "AI Health Copilot <onboarding@resend.dev>",
        "to": [email],
        "subject": "Reset your AI Health Copilot password",
        "html": f"""
            <h2>Password reset</h2>
            <p>Click below to create a new password.</p>
            <p><a href="{reset_url}">Reset my password</a></p>
            <p>This link expires in 30 minutes.</p>
        """,
    })
@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
):
    email = payload.email.strip().casefold()

    with SessionLocal() as db:
        user = db.query(User).filter(
            func.lower(User.email) == email
        ).first()

        if user is not None:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            )
            db.add(reset_record)
            db.commit()

            reset_url = (
                f"{settings.frontend_url}/reset-password?token={token}"
            )
            background_tasks.add_task(
                send_reset_email, email, reset_url
            )

    return {
        "message": "If that email is registered, a password reset link will be sent."
    }

@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    if len(payload.new_password) < 12:
        raise HTTPException(
            status_code=422,
            detail="Password must be at least 12 characters long.",
        )

    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()

    with SessionLocal() as db:
        record = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used.is_(False),
                PasswordResetToken.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

        if record is None:
            raise HTTPException(
                status_code=400,
                detail="This reset link is invalid or expired.",
            )

        user = db.query(User).filter(User.id == record.user_id).first()
        if user is None:
            raise HTTPException(
                status_code=400,
                detail="This reset link is invalid or expired.",
            )

        user.password_hash = hash_password(payload.new_password)
        record.used = True
        db.commit()

    return {"message": "Password reset successfully. You can now log in."}