"""方案 A 多轮生成 — 验收测试 (T1-T5)

在 TDD 阶段先于实现写好。所有断言都基于"实际跑一次多轮生成"的输出。
首次跑会调真实 AI（成本 ~¥0.5），后续可以从 cache 加载。

执行：cd backend && python3 scripts/test_multi_turn_generation.py
"""

import asyncio
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

PASS = f"{GREEN}✓{RESET}"
FAIL = f"{RED}✗{RESET}"
WARN = f"{YELLOW}⚠{RESET}"

CACHE_FILE = PROJECT_ROOT / "data" / "test_multi_turn_cache.txt"
results = []  # (id, name, status, detail)


def _log(tid, name, status, detail=""):
    results.append((tid, name, status, detail))
    s = {"PASS": PASS, "FAIL": FAIL, "SKIP": WARN}.get(status, status)
    print(f"  {s} {tid} {name}{(': ' + detail) if detail else ''}")


def _summary():
    print()
    print("─" * 72)
    p = sum(1 for r in results if r[2] == "PASS")
    f = sum(1 for r in results if r[2] == "FAIL")
    sk = sum(1 for r in results if r[2] == "SKIP")
    print(f"  共 {len(results)} 项：{PASS} {p} · {FAIL} {f} · {WARN} {sk}")
    if f:
        print(f"\n{RED}失败用例：{RESET}")
        for tid, name, _s, d in results:
            if _s == "FAIL":
                print(f"  {FAIL} {tid} {name}: {d}")
    return f == 0


# ──────────────────────────────────────────────────────────────────────
# 生成或加载 fixture
# ──────────────────────────────────────────────────────────────────────

async def generate_chapter(force: bool = False) -> str:
    """生成"服务方案"章节文本，结果缓存到磁盘以避免重复 AI 调用。"""
    if not force and CACHE_FILE.exists():
        text = CACHE_FILE.read_text(encoding="utf-8")
        if len(text) > 1000:
            print(f"  [cache] 加载已有生成结果 ({len(text)} 字，{CACHE_FILE.name})")
            return text

    print("  [生成中] 调用真实 AI（约 30s-3min，~¥0.5）...")
    from app.services.bid_ai_service import bid_ai_service
    from app.database import async_session_factory
    from app.models.bid import BidProject, BidSection
    from sqlalchemy import select

    async with async_session_factory() as db:
        # 找一个含"服务方案"的章节；若无，则伪造一个最小 section
        proj_res = await db.execute(
            select(BidProject).where(BidProject.is_deleted == 0).limit(1)
        )
        project = proj_res.scalar_one_or_none()
        if not project:
            raise RuntimeError("数据库无任何项目，无法测试")

        sec_res = await db.execute(
            select(BidSection).where(
                BidSection.project_id == project.id,
                BidSection.is_deleted == 0,
                BidSection.title.contains("服务方案"),
            ).limit(1)
        )
        section = sec_res.scalar_one_or_none()
        if not section:
            sec_res = await db.execute(
                select(BidSection).where(
                    BidSection.project_id == project.id,
                    BidSection.is_deleted == 0,
                ).limit(1)
            )
            section = sec_res.scalar_one_or_none()
            if not section:
                raise RuntimeError("无可用 section")
            print(f"  [警告] 项目无服务方案章节，复用 section {section.id} ({section.title})")

        # 触发流式生成
        text_buf = []
        progress_count = 0
        async for event in bid_ai_service.generate_section_content_stream(
            db, section.id, tender_requirements=None, additional_context=None
        ):
            if isinstance(event, dict):
                if "content" in event:
                    text_buf.append(event["content"])
                elif "progress" in event:
                    progress_count += 1
                    p = event["progress"]
                    print(f"    [{p.get('current')}/{p.get('total')}] {p.get('subtopic', '?')[:40]}")
            elif isinstance(event, str):
                text_buf.append(event)

        full_text = "".join(text_buf)
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(full_text, encoding="utf-8")
        print(f"  [完成] 生成 {len(full_text)} 字，progress 事件 {progress_count} 个")
        return full_text


# ──────────────────────────────────────────────────────────────────────
# 测试用例
# ──────────────────────────────────────────────────────────────────────

def t1_section_count(text: str):
    name = "≥ 8 个 ## 一级标题（10 项 checklist 至少完成 8 个）"
    headings = re.findall(r'^##\s+[一二三四五六七八九十]+、', text, re.MULTILINE)
    n = len(headings)
    if n >= 8:
        _log("T1", name, "PASS", f"{n} 个 ## 标题")
    else:
        _log("T1", name, "FAIL",
             f"只有 {n} 个 ##。命中标题: {[h.strip() for h in headings]}")


def t2_avg_section_length(text: str):
    name = "平均每个 ## 章节 ≥ 800 字"
    parts = re.split(r'^##\s+', text, flags=re.MULTILINE)[1:]  # 第一段是 ## 之前
    if not parts:
        return _log("T2", name, "FAIL", "未识别到 ## 段")
    counts = [len(p) for p in parts]
    avg = sum(counts) / len(counts)
    if avg >= 800:
        _log("T2", name, "PASS", f"平均 {avg:.0f} 字（{len(counts)} 段）")
    else:
        _log("T2", name, "FAIL",
             f"平均 {avg:.0f} 字 < 800（各段字数：{counts}）")


def t3_total_length(text: str):
    name = "整章字数 ≥ 7000"
    n = len(text)
    if n >= 7000:
        _log("T3", name, "PASS", f"{n} 字")
    else:
        _log("T3", name, "FAIL", f"{n} 字 < 7000")


def t4_quantified_specs(text: str):
    name = "≥ 50 处带数字+单位的量化指标"
    # 匹配「数字 + 常见单位」组合
    pattern = re.compile(
        r'\d+(?:\.\d+)?\s*(?:mm|cm|m|℃|°C|%|％|小时|分钟|秒|天|年|月|日|'
        r'g/㎡|g/m²|MPa|N|kg|条|份|次|项|件|个|包|箱|台|余|多)|'
        r'≤\s*\d+|≥\s*\d+|±\s*\d+'
    )
    hits = pattern.findall(text)
    if len(hits) >= 50:
        _log("T4", name, "PASS", f"{len(hits)} 处")
    else:
        _log("T4", name, "FAIL", f"只有 {len(hits)} 处 < 50")


def t5_no_duplicate_paragraphs(text: str):
    name = "无重复段落（同一长句不在多处出现）"
    # 取 ≥ 30 字的句子去重看
    sentences = [s.strip() for s in re.split(r'[。！？\n]', text) if 30 <= len(s.strip()) <= 200]
    counter = {}
    for s in sentences:
        counter[s] = counter.get(s, 0) + 1
    dupes = [s for s, c in counter.items() if c > 1]
    if not dupes:
        _log("T5", name, "PASS", f"{len(sentences)} 句去重无重复")
    elif len(dupes) <= 2:
        _log("T5", name, "PASS",
             f"轻微重复 {len(dupes)} 处可接受（{dupes[0][:30]}...）")
    else:
        _log("T5", name, "FAIL",
             f"{len(dupes)} 处重复段：[{dupes[0][:50]!r}, ...]")


# ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'═' * 72}")
    print("  方案 A 多轮生成 — 验收测试 (T1-T5)")
    print(f"{'═' * 72}\n")

    force = "--rebuild" in sys.argv
    if force and CACHE_FILE.exists():
        CACHE_FILE.unlink()
        print(f"  [--rebuild] 删除缓存 {CACHE_FILE.name}")

    print("【生成 / 加载章节文本】")
    try:
        text = asyncio.run(generate_chapter(force))
    except Exception as e:
        _log("T0", "生成章节文本", "FAIL", f"{type(e).__name__}: {e}")
        _summary()
        sys.exit(1)

    print("\n【内容质量检查】")
    t1_section_count(text)
    t2_avg_section_length(text)
    t3_total_length(text)
    t4_quantified_specs(text)
    t5_no_duplicate_paragraphs(text)

    ok = _summary()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
