"""把 reference_samples_top.jsonl 灌入 knowledge_template 表

- category='REFERENCE' （新类别，区别于现有 'COMMITMENT' / 'TECH' / 'PRICE'）
- title 形如 「服务方案 — （一）各类印刷工艺掌握」
- tags 含主题 keywords，方便 _get_knowledge_reference 按章节标题命中

幂等：先按 title 软删旧的 REFERENCE 类目再插新的

执行：cd backend && python3 scripts/load_reference_samples.py
"""

import json
import os
import sqlite3
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bid.db")
SAMPLES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reference_samples_top.jsonl")

# category → tags（这些 tags 会被 _get_knowledge_reference 按章节标题关键词匹配）
CATEGORY_TAGS = {
    "服务方案": "服务方案,整体服务,服务承诺,服务流程,响应时间,通用模板",
    "印刷工艺": "印刷工艺,色彩管理,工艺方案,打样,校色,印刷,通用模板",
    "质量控制": "质量控制,质量保证,质量管理,质量管控,通用模板",
    "应急预案": "应急预案,应急响应,紧急订单,通用模板",
    "安全生产": "安全生产,安全管理,安全措施,消防,通用模板",
    "仓储物流": "包装,运输,配送,仓储,物流,通用模板",
    "保密措施": "保密,保密措施,信息安全,通用模板",
    "人员配置": "人员配备,团队,项目组,人员,通用模板",
    "环保措施": "绿色印刷,环保,节能,绿色,VOC,通用模板",
    "售后服务": "售后服务,售后,通用模板",
}


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB 不存在: {DB_PATH}"); sys.exit(1)
    if not os.path.exists(SAMPLES_PATH):
        print(f"❌ 样本不存在: {SAMPLES_PATH}（请先运行 categorize_reference_samples.py）"); sys.exit(1)

    with open(SAMPLES_PATH, encoding="utf-8") as f:
        samples = [json.loads(line) for line in f]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 软删旧的 REFERENCE 类目（保留外键引用）
    c.execute("UPDATE knowledge_template SET is_deleted=1 WHERE category='REFERENCE'")
    deleted = c.rowcount
    print(f"软删旧 REFERENCE 模板 {deleted} 条")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0
    for s in samples:
        cat = s["category"]
        tags = CATEGORY_TAGS.get(cat, "通用模板")
        title = f"{cat} — {s['title']}（真实投标参考）"[:200]
        c.execute("""
            INSERT INTO knowledge_template
              (title, category, content, tags, source_project_id, usage_count,
               remark, created_at, updated_at, is_deleted)
            VALUES (?, 'REFERENCE', ?, ?, NULL, 0, ?, ?, ?, 0)
        """, (
            title,
            s["content"],
            tags,
            f"来源：{s['source']} | 字数：{s['length']} | 命中分：{s['score']}",
            now, now,
        ))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"\n✓ 已插入 {inserted} 条 REFERENCE 样本到 knowledge_template")


if __name__ == "__main__":
    main()
