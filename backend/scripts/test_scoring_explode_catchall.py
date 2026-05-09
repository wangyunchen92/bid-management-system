"""测试 catch-all 父章节下评分项拆子节逻辑

执行：cd backend && python3 scripts/test_scoring_explode_catchall.py
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.models.base import Base
from app.models.bid import BidProject, BidSection, BidScoringItem, BidSectionScoringItem
from app.services.bid_framework_service import BidFrameworkService

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
PASS = f"{GREEN}✓{RESET}"
FAIL = f"{RED}✗{RESET}"


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    fails = 0
    async with Session() as db:
        # 1. 建项目
        proj = BidProject(title="T", tender_id=None, created_by=1, updated_by=1)
        db.add(proj)
        await db.flush()

        # 2. 建模拟章节：技术方案、业绩证明材料、其他相关证明材料(catch-all)
        sec_tech = BidSection(project_id=proj.id, title="技术方案", section_type="AI_GENERATE",
                              sort_order=1, status="PENDING", word_count=0, created_by=1, updated_by=1)
        sec_perf = BidSection(project_id=proj.id, title="业绩证明材料", section_type="LIBRARY",
                              sort_order=2, status="PENDING", word_count=0, created_by=1, updated_by=1)
        sec_catch = BidSection(project_id=proj.id, title="其他相关证明材料", section_type="LIBRARY",
                               sort_order=3, status="PENDING", word_count=0, created_by=1, updated_by=1)
        for s in (sec_tech, sec_perf, sec_catch):
            db.add(s)
        await db.flush()
        created_sections = [sec_tech, sec_perf, sec_catch]

        # 3. 模拟 parse_result.scoring.details
        parse_result = {
            "scoring": {
                "details": [
                    {"category": "技术", "item": "服务方案完整性", "max_score": 10,
                     "criteria": "...", "linked_chapter_hint": "技术方案"},
                    {"category": "技术", "item": "供应商业绩", "max_score": 8,
                     "criteria": "...", "linked_chapter_hint": "业绩证明材料"},
                    # 以下三项命中 catch-all，应拆子节
                    {"category": "商务", "item": "ISO9001认证证书", "max_score": 3,
                     "criteria": "...", "linked_chapter_hint": "其他相关证明材料"},
                    {"category": "商务", "item": "ISO14001认证证书", "max_score": 3,
                     "criteria": "...", "linked_chapter_hint": "其他相关证明材料"},
                    {"category": "商务", "item": "印刷许可证", "max_score": 2,
                     "criteria": "...", "linked_chapter_hint": "其他相关证明材料"},
                    # 同名（应复用，不重复建子节）
                    {"category": "商务", "item": "ISO9001认证证书", "max_score": 2,
                     "criteria": "...", "linked_chapter_hint": "其他相关证明材料"},
                    # 无 hint，跳过关联
                    {"category": "其他", "item": "无关项", "linked_chapter_hint": ""},
                    # hint 未命中任何章节 → 应新建顶级 AI_GENERATE 章节
                    {"category": "技术", "item": "服务方案完整性补充",
                     "criteria": "...", "linked_chapter_hint": "服务方案"},
                    # 同 hint 复用上一节
                    {"category": "技术", "item": "另一项",
                     "criteria": "...", "linked_chapter_hint": "服务方案"},
                ]
            }
        }

        svc = BidFrameworkService()
        scoring_count, link_count, new_sections = await svc._persist_scoring_items(
            db, proj.id, parse_result, created_sections, user_id=1
        )
        new_children = [s for s in new_sections if s.parent_id is not None]
        new_tops = [s for s in new_sections if s.parent_id is None]
        await db.commit()

        # 断言
        def check(label, cond, detail=""):
            nonlocal fails
            if cond:
                print(f"  {PASS} {label}")
            else:
                print(f"  {FAIL} {label}: {detail}")
                fails += 1

        check("T1 共9个评分项落库", scoring_count == 9, f"got {scoring_count}")
        # 链接：catch-all 4 (含同名复用) + 顶级 2 + 新建顶级 2 = 8
        check("T2 链接数 = 8", link_count == 8, f"got {link_count}")
        check("T3 拆出 3 个 catch-all 子章节", len(new_children) == 3, f"got {len(new_children)}")
        check("T3b 新建 1 个顶级章节（hint=服务方案 复用）", len(new_tops) == 1,
              f"got {len(new_tops)} titles={[t.title for t in new_tops]}")
        check("T3c 新建顶级 section_type=AI_GENERATE",
              new_tops[0].section_type == "AI_GENERATE" if new_tops else False,
              f"got {new_tops[0].section_type if new_tops else None}")

        names = sorted(c.title for c in new_children)
        check("T4 子章节名称正确",
              names == sorted(["ISO9001认证证书", "ISO14001认证证书", "印刷许可证"]),
              f"got {names}")

        for c in new_children:
            if c.parent_id != sec_catch.id:
                check(f"T5 子节 {c.title} parent_id 正确", False,
                      f"parent_id={c.parent_id} expected={sec_catch.id}")
                break
        else:
            check("T5 所有子节 parent_id 指向 catch-all 父", True)

        for c in new_children:
            if c.section_type != "LIBRARY":
                check(f"T6 子节 {c.title} section_type=LIBRARY", False, f"got {c.section_type}")
                break
        else:
            check("T6 所有子节 section_type=LIBRARY", True)

        # ISO9001 子节应该被 2 个评分项 link
        iso9001 = next(c for c in new_children if c.title == "ISO9001认证证书")
        link_res = await db.execute(
            select(BidSectionScoringItem).where(BidSectionScoringItem.section_id == iso9001.id)
        )
        iso_links = link_res.scalars().all()
        check("T7 同名 item 复用同一子节，2 条 link", len(iso_links) == 2, f"got {len(iso_links)}")

        # 顶级：原 3 + 新建 1 = 4
        top_res = await db.execute(
            select(BidSection).where(BidSection.project_id == proj.id, BidSection.parent_id.is_(None))
        )
        tops = top_res.scalars().all()
        check("T8 顶级章节 = 4（原 3 + 新建服务方案）", len(tops) == 4, f"got {len(tops)}")

    await engine.dispose()
    print()
    if fails == 0:
        print(f"{GREEN}全部通过{RESET}")
        return 0
    else:
        print(f"{RED}{fails} 项失败{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
