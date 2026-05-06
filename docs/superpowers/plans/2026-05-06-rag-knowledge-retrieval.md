# 实施计划 — 知识库语义检索（RAG）

**日期**：2026-05-06
**分支**：`feature/rag-knowledge-retrieval`
**关联设计**：`docs/superpowers/specs/2026-05-06-rag-knowledge-retrieval-design.md`
**回退点**：commit `dbd32053`（设计稿提交点）

---

## 决策已确认

| 议题 | 决策 |
|---|---|
| embedding 模型 | doubao-embedding-text-240715 |
| 向量库 | numpy + pickle（无新依赖） |
| 数据源 | `reference_samples.jsonl` (195) + `knowledge_template[REFERENCE]` (28) |
| 检索粒度 v1 | 章节级（保留旧接口；v2 可升级到子主题级）|
| top_k / 单段长度 | 6 段 / 800 字截取 |
| 阈值 | 余弦相似度 ≥ 0.55 |
| Fallback | 索引未建 / API 失败 → 自动退回关键词匹配 |
| v2 暂不做 | 业绩/资质向量化、招标文件分段、方案 A 多轮生成、Hybrid 检索 |

---

## 一、Step-by-step 实施

### Step 1：config 加 embedding 模型配置（5 分钟）

**文件**：`backend/app/config.py`

```python
# AI 配置（火山引擎/豆包）部分新增
AI_EMBEDDING_MODEL: str = "doubao-embedding-text-240715"
```

无需改 base_url（共享 ark）。

**验证**：`from app.config import settings; print(settings.AI_EMBEDDING_MODEL)` 不报错。

---

### Step 2：embedding_service.py（约 100 行，30 分钟）

**新文件**：`backend/app/services/embedding_service.py`

核心类：
```python
class EmbeddingService:
    def __init__(self):
        self.client = None
        self._index: Optional[dict] = None  # 内存缓存的索引

    def _get_client(self) -> OpenAI: ...

    def embed_one(self, text: str) -> np.ndarray:
        """单段 embed，返回 (2048,) float32 向量"""

    def embed_batch(self, texts: list[str], batch_size: int = 16) -> np.ndarray:
        """批量 embed，每批 ≤ 16 条避免 API 单次过载"""

    def load_index(self, path: str) -> bool:
        """从 pkl 加载索引到内存；返回 True/False"""

    def search(self, query: str, top_k: int = 6, min_sim: float = 0.55
               ) -> list[tuple[float, dict, str]]:
        """
        query → embed → 余弦相似度 → top-k
        返回 [(similarity, metadata, text), ...]
        """
```

**关键实现细节**：
- 余弦相似度：`np.dot(matrix, q) / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(q))`
- 索引文件 schema：
  ```python
  {
      "model_version": "doubao-embedding-text-240715",
      "built_at": "2026-05-06T12:00:00",
      "vectors": np.ndarray(N, 2048),
      "texts":   list[str],            # 原文
      "metadata": list[dict],          # 每段的 source/title/category/tags
  }
  ```
- 索引加载在 `embedding_service` 单例首次使用时延迟加载，避免启动慢

**验证**：单元测试
```python
emb = embedding_service.embed_one("印刷工艺")
assert emb.shape == (2048,) and emb.dtype == np.float32
```

---

### Step 3：build_reference_embeddings.py（约 80 行，30 分钟）

**新文件**：`backend/scripts/build_reference_embeddings.py`

流程：
1. 读 `data/reference_samples.jsonl` → 195 段
2. 读 DB `knowledge_template WHERE category='REFERENCE'` → 28 段（这部分可能与 jsonl 重叠）
3. **去重**：按 `source + title + content[:100]` 三字段哈希
4. 控制段长 200-3500 字（太短无意义，太长 embedding 质量下降）
5. 批量 embed（每批 16 条），调用次数预估 14 次
6. 序列化保存 `data/reference_embeddings.pkl`
7. 打印：总段数 / API 耗时 / 文件大小

**幂等**：覆盖式重建（删旧文件再写）。

**验证**：
```bash
python3 scripts/build_reference_embeddings.py
# 预期输出：
#   读入 jsonl 195 段 + DB REFERENCE 28 段，去重后 N 段
#   分批 embedding...（共 X 次 API 调用，约 ¥Y）
#   ✓ 已写入 data/reference_embeddings.pkl (~2MB)
ls -lh data/reference_embeddings.pkl  # ~1.5-2.5MB
```

---

### Step 4：bid_ai_service._get_knowledge_reference 改造（30 分钟）

**文件**：`backend/app/services/bid_ai_service.py`

改造目标：

```python
async def _get_knowledge_reference(self, db: AsyncSession, section_title: str) -> str:
    # 1. 优先 RAG 路径
    try:
        from app.services.embedding_service import embedding_service
        if embedding_service.is_loaded():
            results = embedding_service.search(section_title, top_k=6, min_sim=0.55)
            if results:
                return self._format_rag_reference(results)
    except Exception as e:
        logger.warning(f"RAG 检索失败，回退到关键词匹配: {e}")

    # 2. Fallback: 旧的关键词分支（保留现有代码）
    return await self._keyword_reference_fallback(db, section_title)
```

新增 `_format_rag_reference(results)`：
- 标题：`【行业写作风格参考 — 模仿密度和具体度，不要照抄文字】`
- 每段：`--- 参考 N: {title} (来源: {source}, 相似度 {sim:.2f}) ---\n{text[:800]}`
- 末尾："...（共 6 段，按语义相关性排序）"

把当前 `_get_knowledge_reference` 整体逻辑挪到 `_keyword_reference_fallback`，保持向后兼容。

**验证**：单测对比
- "服务方案" 关键词匹配 vs RAG：人工看 RAG 是否返回更具体的工艺/服务段落
- "印刷工艺" 查询：RAG 应该返回烫银/网点/油墨等真正讲工艺的段落

---

### Step 5：服务启动时预加载索引（10 分钟）

**文件**：`backend/app/main.py`（startup event）

```python
@app.on_event("startup")
async def on_startup():
    from app.services.embedding_service import embedding_service
    loaded = embedding_service.load_index("data/reference_embeddings.pkl")
    logger.info(f"RAG 索引加载: {'✓ 成功' if loaded else '✗ 失败/不存在，将走 fallback'}")
```

**验证**：服务启动日志显示加载成功并标注段数。

---

### Step 6：本地端到端验证（20 分钟）

**步骤**：
1. 跑 `python3 scripts/build_reference_embeddings.py`，确认 `data/reference_embeddings.pkl` 生成
2. 重启本地后端，看启动日志确认 RAG 索引加载
3. 写测试脚本 `scripts/test_rag_retrieval.py`：
   ```python
   queries = ["服务方案", "安全生产方案", "应急预案", "印刷工艺及色彩管理方案",
              "保密措施", "售后服务方案", "包装运输配送方案"]
   for q in queries:
       results = embedding_service.search(q, top_k=6)
       print(f"\n=== {q} ===")
       for sim, meta, text in results:
           print(f"  [{sim:.2f}] {meta['title'][:50]}")
           print(f"     {text[:120]}...")
   ```
4. 人工审核：每个 query 的 top 6 中至少有 4 段是真正讲该主题的高密度段落
5. 调用真实生成接口（curl /sections/{id}/ai-generate-stream），观察生成内容是否变得更密

**通过标准**：
- 索引加载日志成功
- 测试脚本输出每个 query 都有 6 段相关结果
- 同一章节 RAG 前后生成对比，量化指标和行业术语数显著增加

---

### Step 7：上线（15 分钟）

```bash
# 1. rsync 代码
rsync -az backend/app/config.py backend/app/main.py \
          backend/app/services/embedding_service.py \
          backend/app/services/bid_ai_service.py \
          backend/scripts/build_reference_embeddings.py \
          root@118.31.237.111:/opt/bid-system/backend/...

# 2. 跑 build（线上消耗 ~¥0.04 一次性）
ssh root@118.31.237.111 "cd /opt/bid-system/backend && \
  ./venv/bin/python3 scripts/build_reference_embeddings.py"

# 3. restart
ssh root@118.31.237.111 "systemctl restart bid-system"

# 4. 验证启动日志含 "RAG 索引加载: ✓ 成功"
```

---

### Step 8：commit + merge（10 分钟）

在 feature 分支上分多次小 commit：
1. `feat(config): add AI_EMBEDDING_MODEL setting`
2. `feat(bid-ai): embedding_service with batch embed + cosine search`
3. `feat(bid-ai): build_reference_embeddings.py for one-off index build`
4. `feat(bid-ai): semantic retrieval in _get_knowledge_reference with keyword fallback`
5. `feat(bid-ai): preload RAG index at startup`

最后 PR 或直接 fast-forward merge 到 master。

---

## 二、文件清单

| 文件 | 改动 | 行数估计 |
|---|---|---|
| `backend/app/config.py` | 修改 | +1 |
| `backend/app/main.py` | 修改 | +5 |
| `backend/app/services/embedding_service.py` | 新增 | +120 |
| `backend/app/services/bid_ai_service.py` | 修改（拆分函数）| +30 / -20 |
| `backend/scripts/build_reference_embeddings.py` | 新增 | +80 |
| `backend/scripts/test_rag_retrieval.py` | 新增（仅本地用，不入 git）| +30 |
| `backend/data/reference_embeddings.pkl` | 新增二进制（不入 git，部署时跑脚本生成）| ~2MB |

---

## 三、回退方案

**单步回退**：
- Step 4 改造后发现 RAG 效果差 → 把 `_get_knowledge_reference` 第一段 try/except 删掉，强制走 fallback；不需要重启服务（代码热重载）
- 索引文件错误 → 直接删 `data/reference_embeddings.pkl`，服务自动走 fallback

**整体回退**：
- `git checkout master`
- 部署回退：rsync master 版本的几个文件，删 `data/reference_embeddings.pkl`，重启服务

---

## 四、测试用例

| # | 用例 | 期望 |
|---|---|---|
| T1 | `embed_one("印刷工艺")` | 返回 (2048,) float32，数值非零 |
| T2 | `embed_batch([...16 条...])` | 返回 (16, 2048)，无 API 错 |
| T3 | `build_reference_embeddings.py` | 生成 pkl，含 ≥ 195 段 |
| T4 | `search("服务方案", k=6)` | 返回 6 段，全部 sim ≥ 0.55 |
| T5 | `search("烫银工艺")` | top 1 是真实投标里讲烫银 160-180℃ 那段（精度验证）|
| T6 | `_get_knowledge_reference("印刷工艺")` (RAG 路径) | 返回包含烫银/网点/油墨密度等具体工艺段 |
| T7 | 删除 pkl 后调用 | 自动 fallback，不报错 |
| T8 | 整章生成对比 | 量化指标数 RAG > 关键词；篇幅 RAG ≥ 关键词 |

---

## 五、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| doubao-embedding API 不稳/超时 | 低 | 检索失败 | 自动 fallback，记录 warning 日志 |
| 索引文件部署遗漏 | 中 | 检索全走 fallback | 部署文档强调；启动日志告警 |
| 195 段中含目录/章节标题等噪音 | 中 | 检索结果含低质段 | 段长过滤 200-3500 字；人工审核前 6 段 |
| 余弦阈值 0.55 不准 | 中 | top 段质量参差 | 实测调优；可改成 0.5 或 0.6 |
| Pkl 内存占用 | 低 | 服务内存 +5MB | 195×2048×4byte = ~1.6MB，可忽略 |
| 索引模型版本与查询不一致 | 低 | 检索结果错乱 | pkl 里存 model_version，查询时校验 |
| 中文 embedding 中标书行业词不准 | 中 | top 段不够精准 | doubao 是主流中文模型，应该够用；后续可换 bge-large-zh |

---

## 六、不在本计划范围内（v2 候选）

- 业绩/资质/设备库语义检索（让 AI 引用最相关的项目）
- 招标文件全文向量化（按章节子主题检索招标里最相关的要求）
- 子主题级 RAG（配合方案 A 多轮生成）
- Hybrid retrieval（关键词召回 + 向量重排）
- 索引在线增量更新接口（管理端上传新参考样本即触发追加 embed）
- BGE / m3e 等开源模型对比

---

## 七、验收清单

- [ ] T1-T8 全部通过
- [ ] 服务启动日志含 "RAG 索引加载: ✓ 成功"
- [ ] 同一"服务方案"章节 RAG 前后生成对比，新版有可见提升（人工审核）
- [ ] Fallback 路径在生产可用（删 pkl 验证）
- [ ] 实施总耗时 ≤ 4 小时
- [ ] 一次建索引成本 ≤ ¥0.1
- [ ] 单次章节生成耗时增加 ≤ 1 秒
- [ ] feature 分支 4-5 个原子 commit，merge 至 master 通过
