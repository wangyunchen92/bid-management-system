# 设计文档 — 知识库语义检索（RAG）

**日期**：2026-05-06
**分支**：`feature/rag-knowledge-retrieval`
**回退点**：commit `3dda0707`（master 最新）
**关联讨论**：AI 生成的方案章节内容深度不够 → 决策 RAG 路径

---

## 一、问题与目标

### 1.1 当前痛点

`bid_ai_service.generate_section_content` 生成方案类章节（服务方案 / 安全生产 / 应急预案 等）时，输出仍然达不到三份真实投标文件那种密度（10930 字、27+ 量化指标、行业术语 + 三级 markdown）。

主要原因之一：**注入 prompt 的「行业写作风格参考」不对症**。

当前实现：
```python
# bid_ai_service._get_knowledge_reference
keywords = self._section_title_to_query_keywords(title)  # 字面映射
WHERE tags LIKE '%服务方案%' OR title LIKE '%服务方案%'
ORDER BY category='REFERENCE' DESC, usage_count DESC
LIMIT 2
```

**问题**：
1. **字面匹配粗糙**：写"工艺执行能力"子主题时，最相关的是真实投标里讲"卡纸封面烫银处理 160-180℃ 3.5-4.0MPa"那段——但因为该段 tags 没"工艺执行"四字，根本拿不到
2. **只取 2 段**：剩余 26 段 REFERENCE 样本和 167 段原文（共 195 段）几乎不被使用
3. **跨表达不识别**："纸张存储防潮" ≠ "仓储管理" → tags LIKE 不命中
4. **样本利用率 < 5%**：每次只命中固定的几条，浪费了真实投标里其他高质量段落

### 1.2 目标

把"关键词字面匹配"换成"**语义向量最近邻检索**"：
- 195 段真实投标段落全部可被命中（按需取最相关的 5-8 段）
- 检索基于**子主题语义**而不是章节标题
- 每个 ## 子主题独立检索，让 AI 看到**对症下药**的参考

**预期效果**：
- AI 看到的参考样本相关性提升 5-10 倍
- 单段参考密度（量化指标 / 行业术语）提升明显
- 章节生成质量更接近真实投标

---

## 二、技术方案

### 2.1 总体架构

```
现有数据
  ├─ data/reference_samples.jsonl              ← 195 段真实投标（已抽取过）
  └─ knowledge_template (REFERENCE 类目)         ← 28 段精选样本（已入库）
                          │
                          ▼
        新增：build_reference_embeddings.py
                          │
        每段调一次 doubao-embedding API
                          │
                          ▼
        data/reference_embeddings.pkl
        ├─ texts:  list[str]                     # 195 段原文
        ├─ vectors: np.ndarray (195, 2048)       # embedding 向量
        ├─ metadata: list[dict]                   # source / title / category / tags
        └─ model_version: str                     # 用哪个模型版本编码

                          │
                          ▼
        bid_ai_service._get_knowledge_reference 改造
                          │
        每次生成时：
          1. 当前任务文本（章节标题 + 子主题 hint）→ embed 一次
          2. cosine similarity vs 195 个候选向量
          3. 取 top 5-8 段返回
                          │
                          ▼
                    注入 AI prompt
```

### 2.2 关键决策

#### 2.2.1 embedding 模型

**选用：`doubao-embedding-text-240715`**

| 候选 | 优点 | 缺点 | 决策 |
|---|---|---|---|
| **doubao-embedding-text-240715** | 中文优化；已经用 ark API 不需新 key；效果好 | 需要 API 调用 | ✅ 选用 |
| OpenAI text-embedding-3-small | 通用强 | 需 OpenAI key 翻墙；中文略弱 | ✗ |
| 开源 m3e-base / bge-base | 本地跑零成本 | 需要 GPU 加速；部署复杂 | ✗ 195 段规模不值得 |

参数：维度 2048（doubao 默认），`encoding_format='float'`。

#### 2.2.2 向量库

**选用：纯 numpy + 单文件 pickle 持久化**

| 候选 | 适用规模 | 复杂度 | 决策 |
|---|---|---|---|
| **numpy + pickle** | < 10000 段，查询 < 100ms | 零依赖 | ✅ 选用 |
| chromadb | 万级 | 装包 ~30MB | ✗ 195 段过度设计 |
| faiss-cpu | 百万级 | C++ 依赖 | ✗ 同上 |
| pgvector | 任意规模 + SQL | 要 Postgres，目前 sqlite | ✗ 整体重构成本高 |

195 段在 numpy 里查一次余弦相似度耗时 < 50ms，零依赖最简洁。

#### 2.2.3 数据源

**当前选用：`data/reference_samples.jsonl`（195 段）**

为什么不用 `knowledge_template` 表的 REFERENCE 类（28 条）？
- 28 条是按"category 分桶 + top N"挑出来的，**剩下 167 条仍然是真投标的干货**，扔了可惜
- jsonl 里每段独立、字数 300-8000 字、含 source / title 元信息，结构清晰
- knowledge_template 表里"通用模板"类（响应函/授权书等）跟 RAG 任务无关，索引时反而是噪音

**未来可选**：把 `lib_achievement` / `lib_qualification` 也向量化，让 AI 写章节时按语义找最相关的业绩/资质（v2 加）。

### 2.3 检索策略

#### 2.3.1 查询粒度

**选用：按章节子主题（## 标题 + hint）查询**

```python
# 当前 bid_ai_service.SECTION_CHECKLIST 已经把每章拆成了多个 ## 子主题
# 例：服务方案 → 10 个 ## ；安全生产 → 5 个 ##

# 现状：整章只查询一次（query = "服务方案"）
# RAG 改造：每个 ## 子主题独立查询
query_text = f"{##标题} {hint}"
# 例："工艺执行能力 按本项目品类至少细分 3 种工艺标准，每种含纸张克重、网点精度..."
```

但**当前 `_get_knowledge_reference` 是章节级调用**（不感知具体 ## 子主题）。两条改造路径：

| 路径 | 描述 | 工作量 |
|---|---|---|
| **路径 1** | RAG 仍然章节级调用（一次查询拿 8 段，喂给整章生成）| 小 |
| 路径 2 | 拆成子主题级（结合方案 A 的多轮生成，每个 ## 独立 RAG）| 大（需先做方案 A）|

**v1 选路径 1**：先做章节级 RAG（不改外部接口），快速看效果。如果方案 A 后续上，路径 2 自然延展。

#### 2.3.2 检索参数

```python
TOP_K = 6                  # 取最近 6 段
MIN_SIMILARITY = 0.55      # 余弦相似度阈值，低于这个的不返回（避免硬塞噪音）
PER_SAMPLE_TRUNCATE = 800  # 每段截 800 字（之前是 1500，现在因为多段所以缩短，总长保持 ~4800）
```

总注入量：6 × 800 = 4800 字（之前 2 × 1500 = 3000 字），相关性提升的同时总量略涨。

#### 2.3.3 fallback

- 如果向量库未建（`reference_embeddings.pkl` 不存在）→ 退回当前的关键词匹配
- 如果 embedding API 失败 → 退回关键词匹配
- 保证 RAG 失败不影响生成，只是参考样本质量降级

### 2.4 数据流变更

```
┌─────────────────────────────────────────────────────────┐
│ 一次性：build_reference_embeddings.py                    │
│   reference_samples.jsonl + knowledge_template REFERENCE │
│        ↓ 195+28 = 223 段（去重后约 195-220）              │
│   逐段 doubao-embedding API                              │
│        ↓                                                 │
│   reference_embeddings.pkl (~2MB)                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 每次生成：bid_ai_service._get_knowledge_reference         │
│   query_text = f"{section_title}"                        │
│        ↓ doubao-embedding 1 次                            │
│   query_vector (2048,)                                   │
│        ↓ numpy cosine similarity                          │
│   top 6 段 + 相似度分数                                   │
│        ↓ 截到 800 字/段                                   │
│   返回拼接好的【行业写作风格参考】块                       │
└─────────────────────────────────────────────────────────┘
```

---

## 三、文件清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `backend/app/config.py` | 修改 | 新增 `AI_EMBEDDING_MODEL` 配置项（默认 `doubao-embedding-text-240715`）|
| `backend/scripts/build_reference_embeddings.py` | 新增 | 从 jsonl + knowledge_template 拉数据，批量 embed，存 pkl |
| `backend/data/reference_embeddings.pkl` | 新增 | 二进制索引文件（不入 git，部署时跑脚本生成）|
| `backend/app/services/embedding_service.py` | 新增 | 封装 doubao-embedding API + 余弦检索 |
| `backend/app/services/bid_ai_service.py` | 修改 | `_get_knowledge_reference` 改用 embedding_service；保留关键词 fallback |
| `backend/requirements.txt` | 不变 | numpy 已有，无新依赖 |

---

## 四、实施步骤

### Step 1：embedding_service.py（约 100 行）
- `EmbeddingService.embed_one(text) → np.ndarray`
- `EmbeddingService.embed_batch(texts: list) → np.ndarray (n, 2048)`，每批 ≤ 32 条避免 API 单次过载
- `EmbeddingService.search(index, query_vector, top_k) → list[(score, metadata)]`
- 单例 `embedding_service`

### Step 2：build_reference_embeddings.py
- 读 `reference_samples.jsonl`（195 段）+ DB 里 `knowledge_template.category='REFERENCE'`（28 段）
- 去重（按 source + title）
- 批量 embed
- 保存 `reference_embeddings.pkl`（含 texts / vectors / metadata / model_version / built_at）
- 幂等：覆盖式重建

### Step 3：bid_ai_service._get_knowledge_reference 改造
- 启动时尝试加载 `reference_embeddings.pkl` 到内存
- 查询：embed 一次 query_text → cosine similarity → top 6
- fallback：未加载/embedding 失败 → 走旧关键词分支

### Step 4：本地端到端验证
- 跑 `build_reference_embeddings.py`
- 写测试脚本：对 5 个章节标题（服务方案/安全生产/应急预案/印刷工艺/保密措施）查询 top 6
- 人工对比检索结果质量 vs 旧关键词匹配

### Step 5：上线
- rsync embedding_service.py + bid_ai_service.py + build 脚本
- 在线上跑 build_reference_embeddings.py（消耗一次 ~¥0.04 API）
- restart 服务
- 浏览器实测："服务方案" AI 生成对比新旧效果

### Step 6：commit + PR/merge
- 在 feature 分支多次 commit
- 验证通过后 merge to master 或 PR

---

## 五、成本

| 项目 | 一次性 | 每份标书（10 章节）|
|---|---|---|
| 建索引（embed 200 段）| **¥0.04** | — |
| 每次生成的 query embed | — | 10 × ¥0.0004 = **¥0.004** |
| 磁盘 | ~2MB | — |
| 新依赖 | 0 | 0 |
| 实施工时 | 3-4 小时 | — |

**结论**：成本可忽略。

---

## 六、风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| doubao-embedding API 不稳定 | 检索失败 | fallback 到关键词匹配 |
| 索引文件丢失（部署清空 data 目录）| 检索失败 | 同上 fallback；部署文档强调 build 脚本 |
| 195 段不够覆盖某些章节类型 | 部分章节查不到优质参考 | 后续用户上传新参考资料追加 embed |
| 余弦相似度阈值不准 | top 段质量参差 | 实施时调优阈值 + 人工检阅 |
| 生成质量提升不达预期 | 决策失误 | RAG 是数据改动，叠加方案 A（多轮生成）才是结构改动；预留 v2 升级 |

---

## 七、不在本设计范围（v2 候选）

- **业绩 / 资质 / 设备的语义检索**：让 AI 写章节时按子主题精准引用最相关的业绩
- **招标文件分段向量化**：写每章时按子主题检索招标里最相关的要求
- **多轮分子主题生成（方案 A）**：每个 ## 独立调 AI（要先有这版 RAG 再叠加效果最好）
- **Hybrid retrieval（关键词 + 向量并行）**：更稳健的检索策略
- **embedding 模型 A/B 测试**：对比 doubao 与开源模型在中文标书语料的效果

---

## 八、验收标准

1. ✅ `build_reference_embeddings.py` 跑通，生成 `reference_embeddings.pkl`，含 ≥ 195 段
2. ✅ `embedding_service.search` 单元测试通过，"工艺执行能力" 查询能返回含烫银/网点/油墨的真实段落
3. ✅ `_get_knowledge_reference("服务方案")` 返回的 6 段相似度 ≥ 0.55
4. ✅ Fallback 路径：删掉 pkl 后调用不报错，自动走关键词分支
5. ✅ 同一章节用 RAG 前后各生成一次，新版生成内容含**明显更多**真实投标里的工艺细节（人工对比）
6. ✅ 生成耗时增加 ≤ 1 秒（额外一次 embed 调用）
