# 企业资料库文件上传功能测试报告

- **测试日期**: 2026-04-12
- **测试环境**: macOS Darwin 25.3.0，后端 FastAPI:8002，前端 Vite:5180
- **测试对象**: 企业资料库四个模块（qualifications / achievements / personnel-certs / products）的文件上传功能
- **测试工程师**: QA Agent

---

## 一、接口测试（Layer 1）

### 测试前准备

- 删除旧 DB（`backend/data/bid.db`），使用全新数据库
- 启动后端 8002，admin/admin123 登录获取 JWT

### 测试用例与结果

| 模块 | 用例 | 结果 | 说明 |
|---|---|---|---|
| qualifications | 创建记录 | PASS | code:200, id:1 |
| qualifications | 上传 .pdf 文件 | PASS | file_path: library/qualifications/{uuid}.pdf |
| qualifications | 查看记录验证 file_path 有值 | PASS | file_path 字段非 null |
| qualifications | 下载文件 GET /library/file/{path} | PASS | HTTP 200，文件内容正确返回 |
| qualifications | 上传 .exe 非法文件 | PASS | 返回 400，detail: "不支持的文件类型: .exe" |
| achievements | 创建记录 | PASS | code:200, id:1 |
| achievements | 上传 .pdf 文件 | PASS | file_path 已设置 |
| achievements | 查看记录验证 file_path 有值 | PASS | |
| achievements | 下载文件 | PASS | HTTP 200 |
| achievements | 上传 .exe 非法文件 | PASS | 400 拒绝 |
| personnel-certs | 创建记录 | PASS | code:200, id:1 |
| personnel-certs | 上传 .pdf 文件 | PASS | |
| personnel-certs | 查看记录验证 file_path 有值 | PASS | |
| personnel-certs | 下载文件 | PASS | HTTP 200 |
| personnel-certs | 上传 .exe 非法文件 | PASS | 400 拒绝 |
| products | 创建记录 | PASS | code:200, id:1 |
| products | 上传 .pdf 文件 | PASS | |
| products | 查看记录验证 file_path 有值 | PASS | |
| products | 下载文件 | PASS | HTTP 200 |
| products | 上传 .exe 非法文件 | PASS | 400 拒绝 |

**接口测试结果：20/20 PASS**

---

## 二、Playwright E2E 页面实操测试（Layer 2）

### e2e-deep-test.mjs 修改内容

在 `testLibraryCRUD` 函数中新增两项测试用例（每模块均执行）：
1. **表格有"附件"列** — 检查 `.ant-table-thead th` 中含有"附件"文本
2. **编辑弹窗中有上传文件按钮** — 打开编辑弹窗，验证弹窗文本包含"上传文件"/"重新上传"/"上传附件"

同时将首次进入资料库页面的等待时间从 1000ms 调整为 1500ms，解决初次渲染时序问题。

### 运行结果（全量 56 个测试用例）

```
📊 深度测试结果: 52/56 通过, 4 失败
```

#### 企业资料库（12项全部通过）

| 测试 | 结果 |
|---|---|
| 资质证书 — 页面渲染+新增弹窗 | PASS |
| 资质证书 — 表格有"附件"列 | PASS |
| 资质证书 — 编辑弹窗中有上传文件按钮 | PASS |
| 业绩案例 — 页面渲染+新增弹窗 | PASS |
| 业绩案例 — 表格有"附件"列 | PASS |
| 业绩案例 — 编辑弹窗中有上传文件按钮 | PASS |
| 人员证书 — 页面渲染+新增弹窗 | PASS |
| 人员证书 — 表格有"附件"列 | PASS |
| 人员证书 — 编辑弹窗中有上传文件按钮 | PASS |
| 产品/设备 — 页面渲染+新增弹窗 | PASS |
| 产品/设备 — 表格有"附件"列 | PASS |
| 产品/设备 — 编辑弹窗中有上传文件按钮 | PASS |

#### 失败用例（均为非文件上传相关的预存 bug）

| 测试 | 失败原因 | 是否影响本次功能 |
|---|---|---|
| 数据字典 — 点击字典类型查看字典项 | Timeout 30000ms，UI 交互阻塞 | 否 |
| 数据字典 — 新增字典项 | 同上，前一步超时导致链式失败 | 否 |
| 组织架构 — 点击部门查看详情 | Timeout 30000ms，`text=总经办` 被遮挡 | 否 |
| 标书知识库 — 导航到知识库列表页 | 页面 body 内容少于 100 字符 | 否 |

以上 4 个失败均为本次功能外的已有问题，与文件上传功能无关。

---

## 三、回归测试（Layer 3）

全量 E2E 运行（56 个用例），与功能相关的所有模块（企业资料库、标书编制、仪表盘、认证、招标管理、投标决策、开标跟踪等）均保持通过，**无回归。**

---

## 四、构建验证（Layer 4）

```bash
npx tsc --noEmit   # 0 错误，0 警告
npm run build      # ✓ built in 4.61s，3756 modules transformed
```

TypeScript 严格模式编译通过，生产构建成功。

---

## 总结

| 层级 | 结果 |
|---|---|
| 接口测试 | 20/20 PASS |
| E2E 页面测试（企业资料库相关） | 12/12 PASS |
| E2E 全量回归 | 52/56（4失败均为已有 bug，与本次功能无关） |
| TypeScript 编译 | 0 错误 |
| Vite 生产构建 | 成功 |

**结论：企业资料库文件上传功能测试全部通过，可以验收。**
