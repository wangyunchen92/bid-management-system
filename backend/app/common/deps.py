"""
依赖注入模块
"""

from typing import Optional

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.common.exceptions import UnauthorizedException
from app.common.security import decode_access_token


async def get_db(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    return session


async def get_current_user_id(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> int:
    if not authorization:
        raise UnauthorizedException("缺少认证信息")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException("无效的认证格式")

    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedException("Token 无效或已过期")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException("Token 中缺少用户信息")

    return int(user_id)


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from app.models.system import SysUser

    result = await db.execute(
        select(SysUser).where(
            SysUser.id == user_id,
            SysUser.is_deleted == 0,
            SysUser.status == 1,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException("用户不存在或已被禁用")

    return user
