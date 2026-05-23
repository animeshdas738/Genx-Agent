from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from src.db import api_keys as api_keys_db
from src.db import users as users_db
from src.models.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyInfo
from src.security import get_current_user

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


async def _get_user_id(username: str) -> int:
    user = await users_db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user["id"]


@router.post("/", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate,
    current_user: str = Depends(get_current_user),
):
    user_id = await _get_user_id(current_user)
    result = await api_keys_db.create_api_key(user_id=user_id, name=body.name)
    return ApiKeyCreated(**result)


@router.get("/", response_model=List[ApiKeyInfo])
async def list_api_keys(current_user: str = Depends(get_current_user)):
    user_id = await _get_user_id(current_user)
    keys = await api_keys_db.get_api_keys_for_user(user_id)
    return [ApiKeyInfo(**k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: int,
    current_user: str = Depends(get_current_user),
):
    user_id = await _get_user_id(current_user)
    revoked = await api_keys_db.revoke_api_key(key_id=key_id, user_id=user_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or already revoked",
        )
