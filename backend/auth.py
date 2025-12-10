from fastapi import Depends, HTTPException, status, Request
from typing import Optional
from sqlmodel import Session
from .database import get_session
from .models import User

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

COOKIE_NAME = "user_id"

def create_access_token(data: dict):
    """
    Mock JWT: just returns the subject (user_id) for the cookie.
    """
    return str(data.get("sub"))

def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    """
    Mock Auth: reads 'user_id' from cookie.
    In real world: verify JWT token.
    """
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    user = session.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def get_current_user_optional(request: Request, session: Session = Depends(get_session)) -> Optional[User]:
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    return session.get(User, int(user_id))

def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    return user

def require_profile_completion(user: User = Depends(get_current_active_user)) -> User:
    """
    Blocks access if profile is incomplete.
    """
    if not user.email or not user.phone:
        # Frontend should catch 403 and redirect to /profile
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Profile incomplete. Please update email and phone."
        )
    return user

def require_admin(user: User = Depends(get_current_active_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user
