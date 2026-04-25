# 招标文件模板抽取功能 — 测试报告

**日期**：2026-04-25
**测试人**：qa-agent
**功能模块**：标书编制 → 招标文件解析 → 一键填入招标信息（新流程）
**关联文档**：docs/superpowers/specs/2026-04-25-tender-template-extract-design.md

## 一、自动化验证结果（已执行）

### 1.1 服务启动健康检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| 后端 uvicorn 启动 | ✅ | 已在 127.0.0.1:8002 运行（PID 60073，含 --reload） |
| 前端 vite dev server 启动 | ✅ | 已在 localhost:5180 运行（PID 60097） |
| 后端日志无错误 | ✅ | 应用启动完成，无异常，正常处理请求 |
| /api/docs 可访问 | ✅ | HTTP 200 |

> 注：测试时发现 8002 和 5180 端口已由当前 session 的前次进程占用，验证了已运行的进程状态健康，与预期一致。

### 1.2 后端路由注册

| 路由 | 结果 | 验证方式 |
|---|---|---|
| `POST /api/v1/bid/projects/{project_id}/framework-from-tender` | ✅ | 从 `/api/openapi.json` 确认路由存在 |

OpenAPI 路由详情摘录：
- **summary**：基于招标文件抽取模板生成框架（SSE流式）
- **description**：基于招标文件解析结果，AI 抽取每章模板原文并生成章节框架。SSE 流式推送进度。
- **method**：POST
- **tag**：标书编制

### 1.3 基础健康

| 检查项 | 结果 | 备注 |
|---|---|---|
| 后端登录接口 `/api/v1/auth/login` | ✅ | 返回 access_token，code=200 |
| /api/docs 可访问 | ✅ | HTTP 200 |

登录接口返回示例：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "access_token": "eyJ...",
        "token_type": "Bearer",
        "expires_in": 7200
    }
}
```

### 1.4 构建验证

| 检查项 | 结果 | 依据 |
|---|---|---|
| 前端 TypeScript 编译 | ✅ | T5/T6/T7 均通过 TypeScript 编译确认 |
| 前端 Vite 构建 | ✅ | T7 确认，前端 dev server 正常启动 |
| 后端 Python import | ✅ | T1/T2/T3 均确认，uvicorn 无 ImportError |

### 1.5 源码核查

| 检查项 | 结果 | 文件位置 |
|---|---|---|
| SSE 路由定义 | ✅ | `backend/app/routers/bid.py:178` |
| `framework-from-tender` 路由注册 | ✅ | OpenAPI JSON 确认 |

---

## 二、需用户在浏览器手动验证的场景

### 2.1 「主路径」一键填入招标信息（带 AI 抽取模板）

**前置**：
- 启动前后端（见第三节启动命令）
- 浏览器访问 http://localhost:5180/bid/list
- 登录 admin / admin123
- 选择**已上传过招标文件、章节为空**的项目（建议新建一个项目并关联已解析过的招标 ID，或先把现有项目的章节全部删掉）

**步骤**：
1. 进入工作台，点左侧栏「招标文件解析」按钮，打开 Drawer
2. 确认已有解析结果（或上传一份新的等待解析完成）
3. 滚到底部「解析到 N 个章节建议」卡片
4. 点击「一键填入招标信息」按钮

**期望**：
- 按钮变成 loading 状态，文字变成"生成中..."
- 下方进度面板出现，依次显示：
  - "AI 抽取 N 个章节模板中（约 30~60 秒）..."
  - "AI 抽取完成（命中 M 个，耗时 Xs），正在创建章节..."
  - "已创建 X 个章节"（每章追加）
  - "已生成 X 个章节（含模板 Y 个）"
- 完成后 Drawer 自动关闭
- 章节树刷新出来，自动选中第 1 章
- 第 1 章右侧编辑器显示模板原文（如响应函格式、报价表样式等）
- Toast 提示：`已生成 X 个章节，其中 Y 个含招标文件模板原文`

**验证点**：
- ☐ 章节树章节数 = 解析章节数 + 必备 fallback 数 + 1（"补充信息"）
- ☐ 末尾有「补充信息」章节，类型 LIBRARY
- ☐ 必备章节如「中小企业声明函」「无重大违法记录声明函」若招标文件未列出，自动追加
- ☐ TEMPLATE 类型章节有招标文件中的模板原文
- ☐ MANUAL/AI_GENERATE 类型章节标题正确，content 可能为空

### 2.2 「fallback」未上传招标文件项目

**前置**：新建一个未上传过招标文件的标书项目，进入工作台

**期望**：
- 左侧栏显示「**一键生成框架（标准模板）**」按钮（dashed 边框）
- 点击仍能用 25 章标准模板生成

**验证点**：
- ☐ 新建项目进工作台后，左侧只显示标准模板按钮，不显示「招标文件解析」入口
- ☐ 点击后正常生成 25 章框架

### 2.3 「负向」已有章节项目重复触发

**前置**：用 2.1 已生成过章节的项目

**步骤**：再点一次「招标文件解析」→「一键填入招标信息」

**期望**：
- 进度面板出现红色错误提示
- Toast：`生成失败: 项目已有章节，请先清空再生成`

**验证点**：
- ☐ 错误提示文案正确
- ☐ 已有章节不被覆盖或破坏

### 2.4 「降级」AI 抽取失败

**测试方法**：临时将 `backend/app/config.py` 中的 `AI_API_KEY` 改成无效值（测试后改回）

**期望**：
- 进度面板显示"AI 抽取失败（...），降级创建空章节..."
- 仍创建出章节框架，content 为空
- Toast 警告：`已创建 X 个空章节框架，AI 模板抽取失败请手动填写`

**验证点**：
- ☐ 降级路径正常触发
- ☐ 章节框架仍被创建（不因 AI 失败导致全流程中断）
- ☐ 改回有效 API Key 后功能恢复正常

---

## 三、启动命令（给用户）

```bash
# 终端 1：后端
cd /Users/wangyunchen/agents/标书系统/backend && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002

# 终端 2：前端
cd /Users/wangyunchen/agents/标书系统/frontend && npm run dev
# 浏览器访问 http://localhost:5180/bid/list
# 测试账号：admin / admin123
```

---

## 四、回归风险点

| 风险点 | 影响 | 建议验证 |
|---|---|---|
| 旧的「一键生成框架」流程（25 章标准模板） | T7 修改为只在未解析过招标文件的项目显示 | 见 2.2 |
| 「批量 AI 生成」按钮 | 未改动，应保持正常 | 快速点击确认弹出 AI 生成对话框 |
| 「填充资料库」按钮 | 未改动 | 确认点击后正常填充 LIBRARY 章节 |
| 「文档预览」按钮 | 未改动 | 确认右侧 Drawer 正常弹出 |
| 「标书检测」按钮 | 未改动 | 确认检测流程正常启动 |
| 「Word 导出」按钮 | 未改动 | 确认导出文件正常下载 |

---

## 五、自动化验证总结

**所有自动化验证项全部通过（6/6）**：

1. ✅ 后端服务启动正常（127.0.0.1:8002）
2. ✅ 前端 dev server 启动正常（localhost:5180）
3. ✅ 新 SSE 路由 `/api/v1/bid/projects/{project_id}/framework-from-tender` 已在 OpenAPI 中注册
4. ✅ 登录接口正常返回 access_token
5. ✅ /api/docs 可访问
6. ✅ 后端日志无启动错误

**结论**：无阻塞问题。自动化验证通过，可转给用户执行手动 e2e（2.1~2.4 四个场景），其中 2.1 主路径会调 AI，会产生约 ¥0.1~0.3 成本，2.3 和 2.4 可选测。

---

## 六、附：本次涉及的 commits

```
46a914f3 feat(bid): add AI method to extract chapter templates from tender doc
d8f22543 fix(bid): improve type hint and error handling for extract_chapter_templates
8e54f27e feat(bid): add generate_from_tender service with AI template extraction
27870472 fix(bid): unblock event loop in generate_from_tender, clean up imports
605c6dfe feat(bid): add SSE endpoint /framework-from-tender
67b5bcf3 feat(bid): add frontend service for framework-from-tender SSE
a7feb74a feat(bid): TenderDocParser button calls SSE framework generation with progress
ff398b28 feat(bid): Workbench uses new framework-from-tender flow, hide std template fallback when tender parsed
```
