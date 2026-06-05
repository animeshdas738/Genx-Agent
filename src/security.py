from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: Optional[str] = Security(oauth2_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> str:
    # Try JWT first
    if token:
        payload = await verify_token(token)
        username: str = payload.get("sub")
        if username:
            return username

    # Fall back to API key
    if api_key:
        from src.db import api_keys as api_keys_db
        user = await api_keys_db.get_user_by_api_key(api_key)
        if user:
            return user["username"]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _truncate_password(password: str) -> str:
    return password.encode("utf-8")[:72].decode("utf-8", errors="ignore")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(_truncate_password(plain_password), hashed_password)


def get_password_hash(password):
    return pwd_context.hash(_truncate_password(password))
