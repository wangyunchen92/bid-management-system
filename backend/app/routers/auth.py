"""
认证路由 /api/v1/auth/*
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id
from app.common.response import success
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshTokenRequest
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/login", summary="用户登录")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    data = await auth_service.login(db, request.username, request.password)
    return success(data=data)


@router.post("/logout", summary="退出登录")
async def logout(user_id: int = Depends(get_current_user_id)):
    return success(message="退出成功")


@router.post("/refresh", summary="刷新 Token")
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    data = await auth_service.refresh_token(db, request.refresh_token)
    return success(data=data)


@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    data = await auth_service.get_current_user_info(db, user_id)
    return success(data=data)


@router.put("/password", summary="修改密码")
async def change_password(
    request: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.change_password(db, user_id, request.old_password, request.new_password)
    return success(message="密码修改成功")
