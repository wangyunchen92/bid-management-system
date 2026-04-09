"""
投标决策服务
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import BusinessException, NotFoundException
from app.common.pagination import PaginationParams, paginate
from app.models.approval import ApprovalInstance
from app.models.decision import BidDecision
from app.models.system import SysUser
from app.models.tender import Tender
from app.schemas.decision import DecisionCreate, DecisionUpdate, DecisionResponse
from app.services.approval_service import approval_service


class DecisionService:

    async def _decision_to_dict(self, db: AsyncSession, decision: BidDecision) -> dict:
        d = DecisionResponse.model_validate(decision).model_dump()

        # 金额转 float
        if d.get("estimated_amount") is not None:
            d["estimated_amount"] = float(d["estimated_amount"])

        # 关联招标信息
        tender_result = await db.execute(
            select(Tender.title, Tender.tender_no).where(Tender.id == decision.tender_id)
        )
        tender_row = tender_result.first()
        if tender_row:
            d["tender_title"] = tender_row[0]
            d["tender_no"] = tender_row[1]

        # 发起人名称
        user_result = await db.execute(
            select(SysUser.real_name).where(SysUser.id == decision.initiator_id)
        )
        d["initiator_name"] = user_result.scalar_one_or_none()

        # 审批状态
        if decision.approval_id:
            approval_result = await db.execute(
                select(ApprovalInstance.status).where(ApprovalInstance.id == decision.approval_id)
            )
            d["approval_status"] = approval_result.scalar_one_or_none()
        else:
            d["approval_status"] = None

        return d

    async def create_decision(self, db: AsyncSession, data: DecisionCreate, user_id: int) -> dict:
        # 验证 tender 存在且未删除
        tender_result = await db.execute(
            select(Tender).where(Tender.id == data.tender_id, Tender.is_deleted == 0)
        )
        tender = tender_result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")

        # 创建决策记录
        decision = BidDecision(
            tender_id=data.tender_id,
            decision_reason=data.decision_reason,
            risk_analysis=data.risk_analysis,
            estimated_amount=data.estimated_amount,
            win_probability=data.win_probability,
            competitors=data.competitors,
            decision_result="PENDING",
            initiator_id=user_id,
            remark=data.remark,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(decision)
        await db.flush()
        await db.refresh(decision)

        # 提交审批
        approval_result = await approval_service.submit(
            db=db,
            title=f"投标决策：{tender.title}",
            biz_type="BID_DECISION",
            biz_id=decision.id,
            approver_id=data.approver_id,
            initiator_id=user_id,
        )

        # 将 approval_id 写回 decision
        decision.approval_id = approval_result["id"]
        decision.updated_by = user_id

        # 更新招标状态为 PENDING（如果尚未是 PENDING）
        if tender.status != "PENDING":
            tender.status = "PENDING"
            tender.updated_by = user_id

        await db.flush()
        await db.refresh(decision)

        return await self._decision_to_dict(db, decision)

    async def list_decisions(
        self,
        db: AsyncSession,
        params: PaginationParams,
        keyword: Optional[str] = None,
        decision_result: Optional[str] = None,
        initiator_id: Optional[int] = None,
    ) -> dict:
        query = select(BidDecision).where(BidDecision.is_deleted == 0)

        if decision_result:
            query = query.where(BidDecision.decision_result == decision_result)
        if initiator_id:
            query = query.where(BidDecision.initiator_id == initiator_id)

        # keyword 按 tender title 过滤：需要子查询
        if keyword:
            tender_ids_result = await db.execute(
                select(Tender.id).where(Tender.title.contains(keyword), Tender.is_deleted == 0)
            )
            tender_ids = [row[0] for row in tender_ids_result.all()]
            query = query.where(BidDecision.tender_id.in_(tender_ids))

        result = await paginate(db, query, params, sort_column=BidDecision.id)
        items = []
        for decision in result["items"]:
            items.append(await self._decision_to_dict(db, decision))
        result["items"] = items
        return result

    async def get_decision(self, db: AsyncSession, decision_id: int) -> dict:
        result = await db.execute(
            select(BidDecision).where(BidDecision.id == decision_id, BidDecision.is_deleted == 0)
        )
        decision = result.scalar_one_or_none()
        if decision is None:
            raise NotFoundException("投标决策不存在")
        return await self._decision_to_dict(db, decision)

    async def update_decision(self, db: AsyncSession, decision_id: int, data: DecisionUpdate, user_id: int) -> dict:
        result = await db.execute(
            select(BidDecision).where(BidDecision.id == decision_id, BidDecision.is_deleted == 0)
        )
        decision = result.scalar_one_or_none()
        if decision is None:
            raise NotFoundException("投标决策不存在")

        if decision.decision_result != "PENDING":
            raise BusinessException("只有待审批的决策可以编辑")

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id
        for key, value in update_data.items():
            setattr(decision, key, value)

        await db.flush()
        await db.refresh(decision)
        return await self._decision_to_dict(db, decision)

    async def delete_decision(self, db: AsyncSession, decision_id: int, user_id: int) -> None:
        result = await db.execute(
            select(BidDecision).where(BidDecision.id == decision_id, BidDecision.is_deleted == 0)
        )
        decision = result.scalar_one_or_none()
        if decision is None:
            raise NotFoundException("投标决策不存在")

        decision.is_deleted = 1
        decision.updated_by = user_id
        await db.flush()

    async def get_by_tender(self, db: AsyncSession, tender_id: int) -> list:
        result = await db.execute(
            select(BidDecision).where(
                BidDecision.tender_id == tender_id,
                BidDecision.is_deleted == 0,
            ).order_by(BidDecision.id.desc())
        )
        items = []
        for decision in result.scalars().all():
            items.append(await self._decision_to_dict(db, decision))
        return items


decision_service = DecisionService()
