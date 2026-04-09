"""
审批服务
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import BusinessException, ForbiddenException, NotFoundException
from app.common.pagination import PaginationParams, paginate
from app.models.approval import ApprovalInstance, ApprovalRecord
from app.models.system import SysUser
from app.schemas.approval import ApprovalInstanceResponse, ApprovalRecordResponse


class ApprovalService:

    async def _get_user_name(self, db: AsyncSession, user_id: int) -> Optional[str]:
        result = await db.execute(select(SysUser.real_name).where(SysUser.id == user_id))
        return result.scalar_one_or_none()

    async def _instance_to_dict(self, db: AsyncSession, inst: ApprovalInstance) -> dict:
        d = ApprovalInstanceResponse.model_validate(inst).model_dump()
        d["initiator_name"] = await self._get_user_name(db, inst.initiator_id)
        d["approver_name"] = await self._get_user_name(db, inst.approver_id)
        return d

    async def _record_to_dict(self, db: AsyncSession, rec: ApprovalRecord) -> dict:
        d = ApprovalRecordResponse.model_validate(rec).model_dump()
        d["operator_name"] = await self._get_user_name(db, rec.operator_id)
        return d

    async def submit(self, db: AsyncSession, title: str, biz_type: str,
                     biz_id: Optional[int], approver_id: int, initiator_id: int) -> dict:
        # 验证审批人存在
        approver = await db.execute(
            select(SysUser).where(SysUser.id == approver_id, SysUser.is_deleted == 0, SysUser.status == 1)
        )
        if approver.scalar_one_or_none() is None:
            raise BusinessException("审批人不存在或已被禁用")

        if approver_id == initiator_id:
            raise BusinessException("不能审批自己发起的申请")

        instance = ApprovalInstance(
            title=title,
            biz_type=biz_type,
            biz_id=biz_id,
            initiator_id=initiator_id,
            approver_id=approver_id,
            status="PENDING",
        )
        db.add(instance)
        await db.flush()

        record = ApprovalRecord(
            instance_id=instance.id,
            operator_id=initiator_id,
            action="SUBMIT",
            comment=f"发起审批，指定审批人",
        )
        db.add(record)
        await db.flush()
        await db.refresh(instance)

        return await self._instance_to_dict(db, instance)

    async def my_pending(self, db: AsyncSession, user_id: int, params: PaginationParams) -> dict:
        query = select(ApprovalInstance).where(
            ApprovalInstance.approver_id == user_id,
            ApprovalInstance.status == "PENDING",
            ApprovalInstance.is_deleted == 0,
        )
        result = await paginate(db, query, params, sort_column=ApprovalInstance.created_at)
        items = []
        for inst in result["items"]:
            items.append(await self._instance_to_dict(db, inst))
        result["items"] = items
        return result

    async def my_initiated(self, db: AsyncSession, user_id: int, params: PaginationParams) -> dict:
        query = select(ApprovalInstance).where(
            ApprovalInstance.initiator_id == user_id,
            ApprovalInstance.is_deleted == 0,
        )
        result = await paginate(db, query, params, sort_column=ApprovalInstance.created_at)
        items = []
        for inst in result["items"]:
            items.append(await self._instance_to_dict(db, inst))
        result["items"] = items
        return result

    async def get_detail(self, db: AsyncSession, instance_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(ApprovalInstance).where(ApprovalInstance.id == instance_id, ApprovalInstance.is_deleted == 0)
        )
        inst = result.scalar_one_or_none()
        if inst is None:
            raise NotFoundException("审批实例不存在")

        if inst.initiator_id != user_id and inst.approver_id != user_id:
            raise ForbiddenException("无权查看此审批")

        inst_dict = await self._instance_to_dict(db, inst)

        records_result = await db.execute(
            select(ApprovalRecord)
            .where(ApprovalRecord.instance_id == instance_id)
            .order_by(ApprovalRecord.created_at.asc())
        )
        records = [await self._record_to_dict(db, r) for r in records_result.scalars().all()]

        return {"instance": inst_dict, "records": records}

    async def approve(self, db: AsyncSession, instance_id: int, user_id: int, comment: Optional[str]) -> dict:
        inst = await self._get_pending_instance(db, instance_id, user_id)

        inst.status = "APPROVED"
        inst.result_comment = comment
        inst.approved_at = datetime.now(timezone.utc)

        db.add(ApprovalRecord(
            instance_id=inst.id, operator_id=user_id, action="APPROVE", comment=comment,
        ))
        await db.flush()
        # 审批回调
        await self._on_approved(db, inst)
        await db.refresh(inst)
        return await self._instance_to_dict(db, inst)

    async def reject(self, db: AsyncSession, instance_id: int, user_id: int, comment: Optional[str]) -> dict:
        inst = await self._get_pending_instance(db, instance_id, user_id)

        inst.status = "REJECTED"
        inst.result_comment = comment
        inst.approved_at = datetime.now(timezone.utc)

        db.add(ApprovalRecord(
            instance_id=inst.id, operator_id=user_id, action="REJECT", comment=comment,
        ))
        await db.flush()
        # 审批回调
        await self._on_rejected(db, inst)
        await db.refresh(inst)
        return await self._instance_to_dict(db, inst)

    async def _on_approved(self, db: AsyncSession, inst: ApprovalInstance) -> None:
        if inst.biz_type == "BID_DECISION" and inst.biz_id:
            from app.models.decision import BidDecision
            from app.models.tender import Tender
            result = await db.execute(select(BidDecision).where(BidDecision.id == inst.biz_id))
            decision = result.scalar_one_or_none()
            if decision:
                decision.decision_result = "PASS"
                tender_result = await db.execute(select(Tender).where(Tender.id == decision.tender_id))
                tender = tender_result.scalar_one_or_none()
                if tender:
                    tender.status = "DECIDED_BID"
            await db.flush()

    async def _on_rejected(self, db: AsyncSession, inst: ApprovalInstance) -> None:
        if inst.biz_type == "BID_DECISION" and inst.biz_id:
            from app.models.decision import BidDecision
            from app.models.tender import Tender
            result = await db.execute(select(BidDecision).where(BidDecision.id == inst.biz_id))
            decision = result.scalar_one_or_none()
            if decision:
                decision.decision_result = "REJECT"
                tender_result = await db.execute(select(Tender).where(Tender.id == decision.tender_id))
                tender = tender_result.scalar_one_or_none()
                if tender:
                    tender.status = "DECIDED_GIVE_UP"
            await db.flush()

    async def transfer(self, db: AsyncSession, instance_id: int, user_id: int,
                       to_user_id: int, comment: Optional[str]) -> dict:
        inst = await self._get_pending_instance(db, instance_id, user_id)

        # 验证转审人
        to_user = await db.execute(
            select(SysUser).where(SysUser.id == to_user_id, SysUser.is_deleted == 0, SysUser.status == 1)
        )
        if to_user.scalar_one_or_none() is None:
            raise BusinessException("转审人不存在或已被禁用")

        inst.approver_id = to_user_id

        db.add(ApprovalRecord(
            instance_id=inst.id, operator_id=user_id, action="TRANSFER",
            comment=comment or f"转审",
        ))
        await db.flush()
        await db.refresh(inst)
        return await self._instance_to_dict(db, inst)

    async def _get_pending_instance(self, db: AsyncSession, instance_id: int, user_id: int) -> ApprovalInstance:
        result = await db.execute(
            select(ApprovalInstance).where(ApprovalInstance.id == instance_id, ApprovalInstance.is_deleted == 0)
        )
        inst = result.scalar_one_or_none()
        if inst is None:
            raise NotFoundException("审批实例不存在")
        if inst.status != "PENDING":
            raise BusinessException("该审批已处理，不可重复操作")
        if inst.approver_id != user_id:
            raise ForbiddenException("你不是当前审批人")
        return inst


approval_service = ApprovalService()
