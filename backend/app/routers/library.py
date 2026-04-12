"""
企业资料库路由
"""

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_user_id, get_db, require_super_admin
from app.common.exceptions import BusinessException, NotFoundException
from app.services.library_ai_service import library_ai_service
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import page_response, success
from app.models.library import Achievement, PersonnelCert, Product, Qualification
from app.schemas.library import (
    AchievementCreate,
    AchievementUpdate,
    PersonnelCertCreate,
    PersonnelCertUpdate,
    ProductCreate,
    ProductUpdate,
    QualificationCreate,
    QualificationUpdate,
)
from app.services.library_service import library_service

router = APIRouter()

# 允许的文件扩展名和大小限制
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

# module -> Model 映射
MODULE_MODEL_MAP = {
    "qualifications": Qualification,
    "achievements": Achievement,
    "personnel-certs": PersonnelCert,
    "products": Product,
}

# 上传目录基路径
UPLOAD_BASE = Path(__file__).parent.parent.parent / "data" / "uploads" / "library"


@router.post("/{module}/recognize", summary="上传文件并AI识别内容")
async def recognize_file(
    module: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传文件，AI 识别内容并返回结构化字段（不创建记录，只返回识别结果）"""
    # 验证 module
    valid_modules = {"qualifications", "achievements", "personnel-certs", "products"}
    if module not in valid_modules:
        raise BusinessException(f"无效的模块: {module}")

    # 验证文件类型
    ext = Path(file.filename).suffix.lower()
    allowed = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    if ext not in allowed:
        raise BusinessException(f"不支持的文件类型: {ext}")

    # 保存临时文件
    import uuid as uuid_mod
    temp_dir = UPLOAD_BASE.parent / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid_mod.uuid4()}{ext}"

    content = await file.read()
    temp_path.write_bytes(content)

    # AI 识别
    recognized = library_ai_service.recognize(str(temp_path), module)

    # 将临时文件移到正式目录
    formal_dir = UPLOAD_BASE / module
    formal_dir.mkdir(parents=True, exist_ok=True)
    formal_filename = f"{uuid_mod.uuid4()}{ext}"
    formal_path = formal_dir / formal_filename
    temp_path.rename(formal_path)

    stored_path = f"library/{module}/{formal_filename}"

    return success(data={
        "recognized_fields": recognized,
        "file_path": stored_path,
        "original_name": file.filename,
    })


@router.post("/{module}/{record_id}/upload-file", summary="上传附件")
async def upload_file(
    module: str,
    record_id: int,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    # 1. 验证 module 合法
    if module not in MODULE_MODEL_MAP:
        raise HTTPException(status_code=400, detail=f"不支持的模块: {module}，可选值: {list(MODULE_MODEL_MAP.keys())}")

    # 2. 验证文件扩展名
    original_name = file.filename or ""
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}，允许: {sorted(ALLOWED_EXTENSIONS)}")

    # 3. 读取文件内容并检查大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过 20MB 限制")

    # 4. 查找对应记录
    Model = MODULE_MODEL_MAP[module]
    result = await db.execute(
        select(Model).where(Model.id == record_id, Model.is_deleted == 0)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail=f"记录 ID={record_id} 不存在")

    # 5. 保存文件
    save_dir = UPLOAD_BASE / module
    save_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{uuid.uuid4()}{ext}"
    file_path = save_dir / file_name
    file_path.write_bytes(content)

    # 6. 更新记录的 file_path 字段（相对路径）
    relative_path = f"library/{module}/{file_name}"
    obj.file_path = relative_path
    obj.updated_by = user_id
    await db.commit()
    await db.refresh(obj)

    return success(data={"file_path": relative_path, "original_name": original_name}, message="上传成功")


@router.get("/file/{file_path:path}", summary="下载/预览文件")
async def download_file(
    file_path: str,
    _: int = Depends(get_current_user_id),
):
    # 防止路径遍历攻击
    full_path = UPLOAD_BASE.parent / file_path
    try:
        full_path = full_path.resolve()
        base = (UPLOAD_BASE.parent).resolve()
        full_path.relative_to(base)
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=400, detail="非法路径")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(str(full_path), filename=full_path.name)


# ================================================================== #
#  资质证书
# ================================================================== #

@router.get("/qualifications")
async def list_qualifications(
    keyword: Optional[str] = Query(default=None),
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await library_service.list_qualifications(db, params, keyword=keyword)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/qualifications")
async def create_qualification(
    data: QualificationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.create_qualification(db, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/qualifications/{item_id}")
async def update_qualification(
    item_id: int,
    data: QualificationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.update_qualification(db, item_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/qualifications/{item_id}")
async def delete_qualification(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await library_service.delete_qualification(db, item_id, user_id)
    return success(message="删除成功")


# ================================================================== #
#  业绩案例
# ================================================================== #

@router.get("/achievements")
async def list_achievements(
    keyword: Optional[str] = Query(default=None),
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await library_service.list_achievements(db, params, keyword=keyword)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/achievements")
async def create_achievement(
    data: AchievementCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.create_achievement(db, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/achievements/{item_id}")
async def update_achievement(
    item_id: int,
    data: AchievementUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.update_achievement(db, item_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/achievements/{item_id}")
async def delete_achievement(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await library_service.delete_achievement(db, item_id, user_id)
    return success(message="删除成功")


# ================================================================== #
#  人员证书
# ================================================================== #

@router.get("/personnel-certs")
async def list_personnel_certs(
    keyword: Optional[str] = Query(default=None),
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await library_service.list_personnel_certs(db, params, keyword=keyword)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/personnel-certs")
async def create_personnel_cert(
    data: PersonnelCertCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.create_personnel_cert(db, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/personnel-certs/{item_id}")
async def update_personnel_cert(
    item_id: int,
    data: PersonnelCertUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.update_personnel_cert(db, item_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/personnel-certs/{item_id}")
async def delete_personnel_cert(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await library_service.delete_personnel_cert(db, item_id, user_id)
    return success(message="删除成功")


# ================================================================== #
#  产品/设备
# ================================================================== #

@router.get("/products")
async def list_products(
    keyword: Optional[str] = Query(default=None),
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await library_service.list_products(db, params, keyword=keyword)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/products")
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.create_product(db, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/products/{item_id}")
async def update_product(
    item_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.update_product(db, item_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/products/{item_id}")
async def delete_product(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await library_service.delete_product(db, item_id, user_id)
    return success(message="删除成功")
