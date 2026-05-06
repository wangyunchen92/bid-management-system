"""为 RAG 知识库语义检索建一次性向量索引

数据来源：
1. data/reference_samples.jsonl（195 段真实投标抽取，含 source / title / category）
2. knowledge_template.category='REFERENCE'（28 条精选样本，category-tags 已分桶）

合并去重后批量调豆包 embedding，结果存 data/reference_embeddings.pkl。

幂等：覆盖式重建。

执行：cd backend && python3 scripts/build_reference_embeddings.py
"""

import hashlib
import json
import pickle
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.services.embedding_service import embedding_service

JSONL_PATH = PROJECT_ROOT / "data" / "reference_samples.jsonl"
DB_PATH = PROJECT_ROOT / "data" / "bid.db"
PKL_PATH = PROJECT_ROOT / "data" / "reference_embeddings.pkl"

MIN_LEN = 200    # 太短的段落 embedding 价值低
MAX_LEN = 3500   # 太长的段落语义会被稀释；超过则截前 3500 字


def _hash_key(source: str, title: str, content: str) -> str:
    """去重 key：source + title + 内容前 100 字"""
    h = hashlib.md5()
    h.update((source or "").encode("utf-8"))
    h.update(b"|")
    h.update((title or "").encode("utf-8"))
    h.update(b"|")
    h.update((content or "")[:100].encode("utf-8"))
    return h.hexdigest()


def load_jsonl_samples() -> list[dict]:
    if not JSONL_PATH.exists():
        print(f"⚠️ {JSONL_PATH} 不存在")
        return []
    samples = []
    with open(JSONL_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                samples.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    print(f"  从 jsonl 读入 {len(samples)} 段")
    return samples


def load_kt_references() -> list[dict]:
    if not DB_PATH.exists():
        print(f"⚠️ {DB_PATH} 不存在")
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, title, category, content, tags "
        "FROM knowledge_template WHERE is_deleted=0 AND category='REFERENCE'"
    )
    rows = c.fetchall()
    conn.close()
    out = []
    for row in rows:
        out.append({
            "source": "knowledge_template",
            "title": row[1] or "",
            "category": row[2] or "",
            "content": row[3] or "",
            "tags": row[4] or "",
            "kt_id": row[0],
            "length": len(row[3] or ""),
        })
    print(f"  从 DB knowledge_template[REFERENCE] 读入 {len(out)} 段")
    return out


def main():
    print(f"\n{'═' * 72}")
    print("  构建 RAG 索引 (reference_embeddings.pkl)")
    print(f"  embedding 模型：{settings.AI_EMBEDDING_MODEL}")
    print(f"{'═' * 72}\n")

    print("【1/4】加载数据源")
    a = load_jsonl_samples()
    b = load_kt_references()

    print("\n【2/4】合并去重 + 长度过滤")
    seen: set[str] = set()
    pool: list[dict] = []
    for s in a + b:
        c = (s.get("content") or "").strip()
        if len(c) < MIN_LEN:
            continue
        if len(c) > MAX_LEN:
            c = c[:MAX_LEN]
        key = _hash_key(s.get("source", ""), s.get("title", ""), c)
        if key in seen:
            continue
        seen.add(key)
        pool.append({
            "text": c,
            "metadata": {
                "source": s.get("source", ""),
                "title": s.get("title", ""),
                "category": s.get("category", ""),
                "tags": s.get("tags", ""),
                "length": len(c),
            },
        })
    print(f"  最终入库 {len(pool)} 段（去重 + 长度 {MIN_LEN}-{MAX_LEN} 过滤）")
    if not pool:
        print("❌ 无可用样本"); sys.exit(1)

    print(f"\n【3/4】批量 embedding（共 {len(pool)} 段，每批 16）")
    t0 = time.time()
    texts = [p["text"] for p in pool]
    vectors = embedding_service.embed_batch(texts, batch_size=16)
    dt = time.time() - t0
    print(f"  ✓ 完成，shape={vectors.shape}, dtype={vectors.dtype}, 耗时 {dt:.1f}s")

    print("\n【4/4】写盘")
    PKL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PKL_PATH, "wb") as f:
        pickle.dump({
            "model_version": settings.AI_EMBEDDING_MODEL,
            "built_at": datetime.now().isoformat(timespec="seconds"),
            "vectors": vectors,
            "texts": texts,
            "metadata": [p["metadata"] for p in pool],
        }, f)
    size_mb = PKL_PATH.stat().st_size / 1024 / 1024
    print(f"  ✓ 已写入 {PKL_PATH} ({size_mb:.2f} MB)")

    print(f"\n✅ 全部完成 — {len(pool)} 段 / {vectors.shape[1]} 维 / 文件 {size_mb:.2f}MB")


if __name__ == "__main__":
    main()
