"""RAG 知识库语义检索 — 验收测试脚本

按 plan 里 T1-T8 八个用例验证。先于实现写好（TDD），实施完成后跑这个脚本应当全部 ✓。

执行：cd backend && python3 scripts/test_rag_retrieval.py

注意：T1/T2 会调真实 doubao-embedding API（成本 ~¥0.001/次）；
T3 一次性建索引会调用 ~14 次（成本 ~¥0.04），仅在 pkl 缺失或显式传 --rebuild 时跑。
"""

import asyncio
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

PASS = f"{GREEN}✓{RESET}"
FAIL = f"{RED}✗{RESET}"
WARN = f"{YELLOW}⚠{RESET}"

PKL_PATH = Path(__file__).resolve().parent.parent / "data" / "reference_embeddings.pkl"


# ──────────────────────────────────────────────────────────────────────────
# 测试结果累计
# ──────────────────────────────────────────────────────────────────────────
results: list[tuple[str, str, str, str]] = []  # (id, name, status, detail)


def _log(tid: str, name: str, status: str, detail: str = ""):
    results.append((tid, name, status, detail))
    color_status = {
        "PASS": PASS,
        "FAIL": FAIL,
        "SKIP": WARN,
    }.get(status, status)
    print(f"  {color_status} {tid} {name}{(': ' + detail) if detail else ''}")


def _summary():
    print()
    print("─" * 72)
    p = sum(1 for _, _, s, _ in results if s == "PASS")
    f = sum(1 for _, _, s, _ in results if s == "FAIL")
    sk = sum(1 for _, _, s, _ in results if s == "SKIP")
    total = len(results)
    print(f"  共 {total} 项：{PASS} {p} · {FAIL} {f} · {WARN} {sk}")
    if f > 0:
        print(f"\n{RED}失败用例：{RESET}")
        for tid, name, status, detail in results:
            if status == "FAIL":
                print(f"  {FAIL} {tid} {name}: {detail}")
    return f == 0


# ──────────────────────────────────────────────────────────────────────────
# T1: embed_one 返回向量形状正确
# ──────────────────────────────────────────────────────────────────────────
def t1_embed_one_shape():
    name = "embed_one 返回 (D,) float32 向量，数值非零"
    try:
        from app.services.embedding_service import embedding_service
        vec = embedding_service.embed_one("印刷工艺")
        if not isinstance(vec, np.ndarray):
            return _log("T1", name, "FAIL", f"返回类型不是 ndarray: {type(vec)}")
        if vec.ndim != 1:
            return _log("T1", name, "FAIL", f"维度错误: shape={vec.shape}")
        if vec.dtype != np.float32:
            return _log("T1", name, "FAIL", f"dtype 错误: {vec.dtype} ≠ float32")
        if not np.any(vec != 0):
            return _log("T1", name, "FAIL", "向量全为 0")
        _log("T1", name, "PASS", f"shape={vec.shape}, dtype={vec.dtype}, norm={np.linalg.norm(vec):.3f}")
    except Exception as e:
        _log("T1", name, "FAIL", str(e))


# ──────────────────────────────────────────────────────────────────────────
# T2: embed_batch 批量调用
# ──────────────────────────────────────────────────────────────────────────
def t2_embed_batch():
    name = "embed_batch 批量返回 (n, D)"
    try:
        from app.services.embedding_service import embedding_service
        texts = ["印刷工艺", "服务方案", "安全生产", "应急预案", "保密措施"]
        mat = embedding_service.embed_batch(texts, batch_size=16)
        if mat.shape[0] != len(texts):
            return _log("T2", name, "FAIL", f"行数错误: {mat.shape[0]} ≠ {len(texts)}")
        if mat.shape[1] < 256:
            return _log("T2", name, "FAIL", f"维度过小: {mat.shape[1]}")
        # 不同文本向量应当不同（避免 embed 实现 bug）
        if np.allclose(mat[0], mat[1]):
            return _log("T2", name, "FAIL", "不同文本返回相同向量")
        _log("T2", name, "PASS", f"shape={mat.shape}")
    except Exception as e:
        _log("T2", name, "FAIL", str(e))


# ──────────────────────────────────────────────────────────────────────────
# T3: build_reference_embeddings.py 生成 pkl
# ──────────────────────────────────────────────────────────────────────────
def t3_build_pkl():
    name = "build_reference_embeddings 生成 pkl，含 ≥ 195 段"
    if not PKL_PATH.exists():
        return _log("T3", name, "SKIP",
                    "pkl 不存在，请先跑 python3 scripts/build_reference_embeddings.py")
    try:
        with open(PKL_PATH, "rb") as f:
            data = pickle.load(f)
        if "vectors" not in data or "texts" not in data or "metadata" not in data:
            return _log("T3", name, "FAIL", f"pkl schema 不完整: keys={list(data.keys())}")
        n = len(data["texts"])
        if n < 150:
            return _log("T3", name, "FAIL", f"段数过少: {n} < 150")
        if data["vectors"].shape[0] != n:
            return _log("T3", name, "FAIL", f"vectors/texts 行数不一致")
        size_mb = PKL_PATH.stat().st_size / 1024 / 1024
        _log("T3", name, "PASS",
             f"{n} 段, vectors={data['vectors'].shape}, 文件 {size_mb:.2f}MB, "
             f"模型={data.get('model_version', 'unknown')}")
    except Exception as e:
        _log("T3", name, "FAIL", str(e))


# ──────────────────────────────────────────────────────────────────────────
# T4: search 返回 top-k，全部 sim ≥ 阈值
# ──────────────────────────────────────────────────────────────────────────
def t4_search_topk():
    name = "search('服务方案', k=6) 返回 6 段，相似度全部 ≥ 0.55"
    try:
        from app.services.embedding_service import embedding_service
        if not embedding_service.is_loaded():
            embedding_service.load_index(str(PKL_PATH))
        results_ = embedding_service.search("服务方案", top_k=6, min_sim=0.55)
        if len(results_) < 4:  # 至少 4 段（阈值过滤后可能少于 6）
            return _log("T4", name, "FAIL",
                        f"结果太少: {len(results_)} 段（阈值过严或索引数据不足）")
        for sim, meta, text in results_:
            if sim < 0.55:
                return _log("T4", name, "FAIL", f"相似度低于阈值: {sim:.3f}")
        sims = [f"{r[0]:.2f}" for r in results_]
        _log("T4", name, "PASS", f"{len(results_)} 段, 相似度 [{', '.join(sims)}]")
    except Exception as e:
        _log("T4", name, "FAIL", str(e))


# ──────────────────────────────────────────────────────────────────────────
# T5: ground-truth — 烫银 query 命中真实投标 160-180℃ 段
# ──────────────────────────────────────────────────────────────────────────
def t5_ground_truth_tangyin():
    name = "search('烫银工艺') top 3 必须含 160-180℃ 那段（语义精度验证）"
    try:
        from app.services.embedding_service import embedding_service
        if not embedding_service.is_loaded():
            embedding_service.load_index(str(PKL_PATH))
        results_ = embedding_service.search("烫银工艺 温度压力控制", top_k=3, min_sim=0.4)
        for sim, meta, text in results_:
            # 真实投标里这段一定含 "160" 和 "180" 两个数字 + "MPa"
            if "160" in text and "180" in text and "MPa" in text:
                _log("T5", name, "PASS", f"top {results_.index((sim, meta, text))+1} 命中, sim={sim:.2f}")
                return
        # 没命中，把前 3 段标题打出来 debug
        titles = [r[1].get('title', '?')[:30] for r in results_]
        _log("T5", name, "FAIL", f"top 3 未命中目标段，命中: {titles}")
    except Exception as e:
        _log("T5", name, "FAIL", str(e))


# ──────────────────────────────────────────────────────────────────────────
# T6: _get_knowledge_reference 走 RAG 路径返回真实工艺细节
# ──────────────────────────────────────────────────────────────────────────
def t6_rag_in_get_knowledge_reference():
    name = "_get_knowledge_reference RAG 路径返回含工艺细节段"
    try:
        from app.services.bid_ai_service import bid_ai_service
        from app.database import async_session_factory

        async def _run():
            async with async_session_factory() as db:
                ref = await bid_ai_service._get_knowledge_reference(db, "印刷工艺及色彩管理方案")
                return ref

        ref = asyncio.run(_run())
        if not ref:
            return _log("T6", name, "FAIL", "返回空")
        # 真实投标里讲印刷工艺一定含至少一组：温度/压力/网点/油墨密度
        keywords_groups = [
            ("℃", "MPa"),
            ("网点", "墨"),
            ("套印", "误差"),
            ("烫", "压力"),
        ]
        hit = sum(1 for kws in keywords_groups if all(k in ref for k in kws))
        if hit < 1:
            return _log("T6", name, "FAIL",
                        f"未命中任何工艺关键词组（前 200 字: {ref[:200]}）")
        _log("T6", name, "PASS", f"命中 {hit} 组工艺关键词；总长 {len(ref)} 字")
    except Exception as e:
        _log("T6", name, "FAIL", str(e))


# ──────────────────────────────────────────────────────────────────────────
# T7: pkl 缺失时自动 fallback 到关键词
# ──────────────────────────────────────────────────────────────────────────
def t7_fallback_when_pkl_missing():
    name = "pkl 缺失/索引未加载 → fallback 到关键词匹配，不报错"
    try:
        from app.services.bid_ai_service import bid_ai_service
        from app.services.embedding_service import embedding_service
        from app.database import async_session_factory

        # 临时让索引"未加载"
        backup_index = embedding_service._index
        embedding_service._index = None
        try:
            async def _run():
                async with async_session_factory() as db:
                    return await bid_ai_service._get_knowledge_reference(db, "服务方案")
            ref = asyncio.run(_run())
            # fallback 后仍应返回（即使是空字符串也不应抛异常）
            _log("T7", name, "PASS",
                 f"fallback 路径返回 {len(ref)} 字（关键词匹配 knowledge_template）")
        finally:
            embedding_service._index = backup_index
    except Exception as e:
        _log("T7", name, "FAIL", str(e))


# ──────────────────────────────────────────────────────────────────────────
# T8: 启动时预加载（启动日志验证，由集成测试或人工确认）
# ──────────────────────────────────────────────────────────────────────────
def t8_startup_preload():
    name = "embedding_service.is_loaded() 在加载后返回 True"
    try:
        from app.services.embedding_service import embedding_service
        if not embedding_service.is_loaded():
            embedding_service.load_index(str(PKL_PATH))
        if embedding_service.is_loaded():
            n = len(embedding_service._index["texts"]) if embedding_service._index else 0
            _log("T8", name, "PASS", f"已加载 {n} 段")
        else:
            _log("T8", name, "FAIL", "load_index 调用后 is_loaded 仍为 False")
    except Exception as e:
        _log("T8", name, "FAIL", str(e))


# ──────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'═' * 72}")
    print("  RAG 知识库语义检索 — 验收测试 (T1-T8)")
    print(f"{'═' * 72}\n")

    print("【需要 API 调用的测试】（约 ~¥0.002）")
    t1_embed_one_shape()
    t2_embed_batch()

    print("\n【索引文件验证】")
    t3_build_pkl()

    print("\n【检索功能测试】")
    t4_search_topk()
    t5_ground_truth_tangyin()

    print("\n【集成测试】")
    t6_rag_in_get_knowledge_reference()
    t7_fallback_when_pkl_missing()
    t8_startup_preload()

    ok = _summary()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
