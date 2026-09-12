from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.security.audit import audit_security_event
from app.security.auth import get_current_user
from app.security.jwt import create_access_token
from app.security.models import Role, UserContext
from app.schemas.user import LoginRequest, SignupRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    existing = repo.get_by_email(request.email)
    if existing is not None:
        audit_security_event(
            event="signup_failure",
            user_id=request.email,
            resource="auth",
            action="signup",
            allowed=False,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    from pwdlib import PasswordHash

    password_hash = PasswordHash.recommended()
    hashed_password = password_hash.hash(request.password)

    from app.db.models.user import User

    # First admin is auto-created; subsequent signups get user role
    has_admin = repo.exists_admin()

    new_user = User(
        email=request.email,
        hashed_password=hashed_password,
        full_name=request.full_name,
        role="user" if has_admin else "admin",
        is_active=True,
        is_verified=not has_admin,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    role = Role(new_user.role)
    access_token = create_access_token(
        user_id=str(new_user.id),
        role=role,
    )

    audit_security_event(
        event="signup_success",
        user_id=str(new_user.id),
        resource="auth",
        action="signup",
        allowed=True,
    )

    return TokenResponse(
        access_token=access_token,
        user_id=new_user.id,
        role=role.value,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    user = repo.get_by_email(request.email)

    if user is None or not user.is_active:
        audit_security_event(
            event="login_failure",
            user_id=request.email,
            resource="auth",
            action="login",
            allowed=False,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    from pwdlib import PasswordHash

    password_hash = PasswordHash.recommended()
    if not password_hash.verify(
        request.password,
        user.hashed_password,
    ):
        audit_security_event(
            event="login_failure",
            user_id=str(user.id),
            resource="auth",
            action="login",
            allowed=False,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    try:
        role = Role(user.role)
    except ValueError:
        role = Role.USER

    access_token = create_access_token(
        user_id=str(user.id),
        role=role,
    )

    audit_security_event(
        event="login_success",
        user_id=str(user.id),
        resource="auth",
        action="login",
        allowed=True,
    )

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        role=role.value,
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    user = repo.get_by_id(current_user.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.post("/promote/{user_id}", response_model=UserResponse)
def promote_user(
    user_id: str,
    target_role: Role = Query(..., description="Role to assign: user, analyst, or admin"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can promote users",
        )

    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.role = target_role.value
    db.commit()
    db.refresh(user)

    audit_security_event(
        event="user_promoted",
        user_id=str(current_user.user_id),
        resource="auth",
        action="promote",
        allowed=True,
    )

    return user
