"""
招投标管理平台 - FastAPI 应用入口
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import close_db, init_db, async_session_factory
from app.common.exceptions import (
    BusinessException,
    NotFoundException,
    ForbiddenException,
    UnauthorizedException,
)
from app.common.response import ResponseModel

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动中...")
    await init_db()
    await _init_base_data()
    yield
    await close_db()
    logger.info("应用已关闭")


app = FastAPI(
    title="招投标管理平台",
    description="招投标管理平台后端 API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response


@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(status_code=200, content=ResponseModel(code=exc.code, message=exc.message, data=None).model_dump())


@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(status_code=404, content=ResponseModel(code=404, message=exc.message, data=None).model_dump())


@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    return JSONResponse(status_code=403, content=ResponseModel(code=403, message=exc.message, data=None).model_dump())


@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(status_code=401, content=ResponseModel(code=401, message=exc.message, data=None).model_dump())


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content=ResponseModel(code=500, message="服务器内部错误", data=None).model_dump())


# 注册路由
from app.routers import auth, system, approval, tender, decision, opening, library, bid, tender_doc, dashboard, knowledge, bid_detect

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证管理"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统管理"])
app.include_router(approval.router, prefix="/api/v1/approval", tags=["审批管理"])
app.include_router(tender.router, prefix="/api/v1/tender", tags=["招标管理"])
app.include_router(decision.router, prefix="/api/v1/decision", tags=["投标决策"])
app.include_router(opening.router, prefix="/api/v1/opening", tags=["开标跟踪"])
app.include_router(library.router, prefix="/api/v1/library", tags=["企业资料库"])
app.include_router(bid.router, prefix="/api/v1/bid", tags=["标书编制"])
app.include_router(bid_detect.router, prefix="/api/v1/bid", tags=["标书检测"])
app.include_router(tender_doc.router, prefix="/api/v1/tender-doc", tags=["招标文件解析"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["仪表盘"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["标书知识库"])


@app.get("/api/health", tags=["健康检查"])
async def health_check():
    return ResponseModel(code=200, message="ok", data={"status": "healthy"})


async def _init_base_data():
    from sqlalchemy import select
    from app.models.system import SysUser, SysDictType
    from app.common.security import hash_password

    async with async_session_factory() as session:
        result = await session.execute(
            select(SysUser).where(SysUser.username == "admin")
        )
        if not result.scalar_one_or_none():
            admin = SysUser(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="系统管理员",
                phone="13800000000",
                role="SUPER_ADMIN",
                status=1,
            )
            session.add(admin)
            await session.commit()
            logger.info("默认管理员 admin/admin123 已创建")

        # 创建默认部门
        from app.models.system import SysDepartment
        dept_result = await session.execute(select(SysDepartment).limit(1))
        if not dept_result.scalar_one_or_none():
            root_dept = SysDepartment(
                dept_name="总经办",
                dept_code="ROOT",
                parent_id=None,
                sort_order=0,
                status=1,
            )
            session.add(root_dept)
            await session.commit()
            logger.info("默认部门 '总经办' 已创建")

            # 将 admin 分配到默认部门
            admin_result = await session.execute(
                select(SysUser).where(SysUser.username == "admin")
            )
            admin_user = admin_result.scalar_one_or_none()
            if admin_user:
                admin_user.dept_id = root_dept.id
                await session.commit()

        # 初始化角色
        from app.models.system import SysRole, SysUserRole
        role_result = await session.execute(select(SysRole).limit(1))
        if not role_result.scalar_one_or_none():
            roles_data = [
                ("超级管理员", "SUPER_ADMIN", "拥有全部权限", 0),
                ("管理员", "ADMIN", "日常管理操作", 1),
                ("普通用户", "USER", "基础查看操作", 2),
            ]
            role_map = {}
            for name, code, desc, sort in roles_data:
                role = SysRole(role_name=name, role_code=code, description=desc, sort_order=sort, status=1)
                session.add(role)
                await session.flush()
                role_map[code] = role.id

            # admin 关联 SUPER_ADMIN
            admin_result = await session.execute(
                select(SysUser).where(SysUser.username == "admin")
            )
            admin_user = admin_result.scalar_one_or_none()
            if admin_user and "SUPER_ADMIN" in role_map:
                session.add(SysUserRole(user_id=admin_user.id, role_id=role_map["SUPER_ADMIN"]))

            await session.commit()
            logger.info("预置角色已创建，admin 已关联 SUPER_ADMIN")

        # 初始化字典数据
        dict_check = await session.execute(select(SysDictType).limit(1))
        if not dict_check.scalar_one_or_none():
            await _init_dict_data(session)
            logger.info("预置字典数据已初始化")


async def _init_dict_data(session):
    from app.models.system import SysDictType, SysDictItem

    DICT_DATA = [
        {
            "dict_code": "tender_method",
            "dict_name": "招标方式",
            "items": [
                ("公开招标", "PUBLIC"),
                ("邀请招标", "INVITE"),
                ("竞争性谈判", "NEGOTIATE"),
                ("询价", "INQUIRY"),
                ("单一来源", "SINGLE"),
            ],
        },
        {
            "dict_code": "tender_source",
            "dict_name": "信息来源",
            "items": [
                ("政府采购网", "GOV"),
                ("招标信息网", "BID_INFO"),
                ("企业直邀", "DIRECT"),
                ("中介推荐", "AGENT"),
                ("其他", "OTHER"),
            ],
        },
        {
            "dict_code": "bid_status",
            "dict_name": "投标状态",
            "items": [
                ("待评估", "PENDING"),
                ("已决策-投标", "DECIDED_BID"),
                ("已决策-放弃", "DECIDED_GIVE_UP"),
                ("编制中", "COMPOSING"),
                ("已提交", "SUBMITTED"),
                ("已开标", "OPENED"),
            ],
        },
        {
            "dict_code": "decision_result",
            "dict_name": "决策结果",
            "items": [
                ("通过", "PASS"),
                ("不通过", "REJECT"),
                ("待定", "PENDING"),
            ],
        },
        {
            "dict_code": "opening_result",
            "dict_name": "开标结果",
            "items": [
                ("中标", "WIN"),
                ("未中标", "LOSE"),
                ("废标", "INVALID"),
                ("流标", "ABORTED"),
            ],
        },
        {
            "dict_code": "doc_type",
            "dict_name": "标书文档类型",
            "items": [
                ("技术方案", "TECH"),
                ("商务报价", "COMMERCIAL"),
                ("资质文件", "QUALIFICATION"),
                ("承诺函", "COMMITMENT"),
                ("其他", "OTHER"),
            ],
        },
        {
            "dict_code": "cert_type",
            "dict_name": "资质证书类型",
            "items": [
                ("营业执照", "BUSINESS_LICENSE"),
                ("资质证书", "QUALIFICATION"),
                ("ISO认证", "ISO"),
                ("安全生产许可证", "SAFETY"),
                ("其他", "OTHER"),
            ],
        },
        {
            "dict_code": "urgency",
            "dict_name": "紧急程度",
            "items": [
                ("正常", "NORMAL"),
                ("紧急", "URGENT"),
                ("特急", "CRITICAL"),
            ],
        },
    ]

    for idx, entry in enumerate(DICT_DATA):
        dict_type = SysDictType(
            dict_name=entry["dict_name"],
            dict_code=entry["dict_code"],
            status=1,
        )
        session.add(dict_type)
        await session.flush()  # get dict_type.id

        for sort_idx, (label, value) in enumerate(entry["items"]):
            item = SysDictItem(
                dict_type_id=dict_type.id,
                item_label=label,
                item_value=value,
                sort_order=sort_idx,
                status=1,
            )
            session.add(item)

    await session.commit()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.APP_DEBUG)
