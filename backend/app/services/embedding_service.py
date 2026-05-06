"""文本 embedding 服务 + 余弦最近邻检索（RAG 知识库语义检索）

底层用豆包 Doubao-embedding-vision 多模态向量模型，通过 multimodal
API 接收纯文本输入，统一映射到 2048 维向量空间。

豆包 multimodal API 单次只能处理一段输入，批量时用 asyncio 并发降低总耗时。
"""

import asyncio
import logging
import pickle
import time
from pathlib import Path
from typing import Optional

import httpx
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

EMBED_URL = f"{settings.AI_BASE_URL.rstrip('/')}/embeddings/multimodal"
HTTP_TIMEOUT = 60.0  # 单次 embed
MAX_CONCURRENCY = 16  # 批量调用时的最大并发


class EmbeddingService:
    """单例：封装 doubao-embedding-vision multimodal API + 内存索引检索"""

    def __init__(self):
        self._index: Optional[dict] = None  # 索引内存缓存

    # ── HTTP 调用底层 ─────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.AI_API_KEY}",
            "Content-Type": "application/json",
        }

    def _payload(self, text: str) -> dict:
        return {
            "model": settings.AI_EMBEDDING_MODEL,
            "input": [{"type": "text", "text": text}],
            "encoding_format": "float",
        }

    def _parse(self, resp_json: dict) -> np.ndarray:
        """multimodal API 返回 data.embedding 是单个数组（不是 list）"""
        data = resp_json.get("data")
        if isinstance(data, dict) and "embedding" in data:
            return np.asarray(data["embedding"], dtype=np.float32)
        if isinstance(data, list) and data and "embedding" in data[0]:
            return np.asarray(data[0]["embedding"], dtype=np.float32)
        raise ValueError(f"无法从响应解析 embedding: keys={list(resp_json.keys())}")

    # ── 单段 embed（同步）────────────────────────────────────

    def embed_one(self, text: str) -> np.ndarray:
        if not text or not text.strip():
            raise ValueError("embed_one: 输入文本为空")
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            r = client.post(EMBED_URL, headers=self._headers(), json=self._payload(text))
            r.raise_for_status()
            return self._parse(r.json())

    # ── 批量 embed（asyncio 并发）─────────────────────────────

    async def _embed_one_async(self, client: httpx.AsyncClient,
                                sem: asyncio.Semaphore, text: str) -> np.ndarray:
        async with sem:
            r = await client.post(EMBED_URL, headers=self._headers(),
                                  json=self._payload(text), timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            return self._parse(r.json())

    async def _embed_batch_async(self, texts: list[str],
                                  concurrency: int) -> np.ndarray:
        sem = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient() as client:
            tasks = [self._embed_one_async(client, sem, t) for t in texts]
            vecs = await asyncio.gather(*tasks)
        return np.vstack(vecs)

    def embed_batch(self, texts: list[str], batch_size: int = 16) -> np.ndarray:
        """批量 embed，asyncio 并发；batch_size 解释为最大并发数"""
        if not texts:
            raise ValueError("embed_batch: 输入为空")
        valid = [t for t in texts if t and t.strip()]
        if not valid:
            raise ValueError("embed_batch: 所有输入为空")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在已有事件循环里（如 FastAPI），复用 run_in_executor 起新 loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(
                        asyncio.run, self._embed_batch_async(valid, batch_size)
                    ).result()
        except RuntimeError:
            pass
        return asyncio.run(self._embed_batch_async(valid, batch_size))

    # ── 索引加载 / 检索 ───────────────────────────────────────

    def load_index(self, path: str) -> bool:
        p = Path(path)
        if not p.exists():
            logger.warning(f"[RAG] 索引文件不存在: {p}")
            self._index = None
            return False
        try:
            with open(p, "rb") as f:
                data = pickle.load(f)
            for required in ("vectors", "texts", "metadata"):
                if required not in data:
                    logger.error(f"[RAG] 索引文件缺少字段 {required}: {p}")
                    self._index = None
                    return False
            n = len(data["texts"])
            if data["vectors"].shape[0] != n:
                logger.error(f"[RAG] vectors/texts 行数不一致")
                self._index = None
                return False
            # 预归一化（节省每次查询的开销）
            vecs = data["vectors"].astype(np.float32, copy=False)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            data["vectors_norm"] = vecs / norms
            self._index = data
            logger.info(
                f"[RAG] 索引加载成功: {n} 段 | model={data.get('model_version', '?')} | "
                f"built_at={data.get('built_at', '?')}"
            )
            return True
        except Exception as e:
            logger.exception(f"[RAG] 索引加载失败: {e}")
            self._index = None
            return False

    def is_loaded(self) -> bool:
        return self._index is not None

    def search(self, query: str, top_k: int = 6, min_sim: float = 0.55
               ) -> list[tuple[float, dict, str]]:
        if not self.is_loaded():
            raise RuntimeError("RAG 索引未加载，请先调用 load_index()")

        q_vec = self.embed_one(query)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_unit = q_vec / q_norm

        sims = self._index["vectors_norm"] @ q_unit
        n = sims.shape[0]
        k = min(top_k, n)
        top_indices = np.argpartition(sims, -k)[-k:]
        top_indices = top_indices[np.argsort(-sims[top_indices])]

        results: list[tuple[float, dict, str]] = []
        for idx in top_indices:
            sim = float(sims[idx])
            if sim < min_sim:
                continue
            results.append((sim, self._index["metadata"][idx], self._index["texts"][idx]))
        return results


# 单例
embedding_service = EmbeddingService()
