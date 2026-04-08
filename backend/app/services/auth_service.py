"""
认证服务
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import BusinessException, UnauthorizedException
from app.common.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.models.system import SysUser


class AuthService:

    async def login(self, db: AsyncSession, username: str, password: str) -> dict:
        result = await db.execute(
            select(SysUser).where(SysUser.username == username, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise BusinessException("用户名或密码错误")
        if user.status != 1:
            raise BusinessException("账号已被禁用")
        if not verify_password(password, user.password_hash):
            raise BusinessException("用户名或密码错误")

        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        user.last_login_at = datetime.now(timezone.utc)
        await db.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def refresh_token(self, db: AsyncSession, refresh_token: str) -> dict:
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            raise UnauthorizedException("Refresh Token 无效或已过期")

        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException("Token 中缺少用户信息")

        result = await db.execute(
            select(SysUser).where(SysUser.id == int(user_id), SysUser.is_deleted == 0, SysUser.status == 1)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UnauthorizedException("用户不存在或已被禁用")

        token_data = {"sub": str(user.id)}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
            "token_type": "Bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def get_current_user_info(self, db: AsyncSession, user_id: int) -> dict:
        result = await db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UnauthorizedException("用户不存在")

        is_super_admin = user.role == "SUPER_ADMIN"
        permissions = ["*"] if is_super_admin else []

        return {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "phone": user.phone,
            "email": user.email,
            "avatar": user.avatar,
            "role": user.role,
            "permissions": permissions,
        }

    async def change_password(self, db: AsyncSession, user_id: int, old_password: str, new_password: str) -> bool:
        result = await db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException("用户不存在")
        if not verify_password(old_password, user.password_hash):
            raise BusinessException("旧密码不正确")

        user.password_hash = hash_password(new_password)
        await db.flush()
        return True


auth_service = AuthService()
