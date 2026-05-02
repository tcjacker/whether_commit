# 技术方案文档（轻量版）：whether_commit

## 1. 文档目标
本方案是在原研发版 PRD 基础上，为 **whether_commit MVP 阶段**重新收敛的轻量级技术设计，核心目标是协助判断当前代码变更是否应该提交。

目标是：

- 不引入数据库
- 不引入 Redis
- 不引入任务队列
- 不做复杂分布式调度

而是用：

- **单进程 FastAPI 服务**
- **本地文件快照存储**
- **进程内内存缓存**
- **后台任务 + SSE / 轮询**
- **外部工具适配器**

快速实现一个可运行的系统，验证以下核心价值：

1. 自动生成工程全貌
2. 自动识别主要能力、主路径、系统结构
3. 将当前待提交的 AI 改动挂到工程全貌图上
4. 展示当前验证状态与未覆盖风险

### 1.1 “最近 AI 改动”口径
本方案中的“最近 AI 改动”统一指当前 Git 工作区中尚未提交的改动集合，而不是最近一次 commit。

默认分析范围：

- staged changes
- unstaged changes
- 未被 `.gitignore` 忽略的源码类 / 配置类 untracked files

默认比较基线：

- `HEAD`

因此，变更分析统一基于 `HEAD + 当前工作区待提交内容` 生成。

---

## 2. 设计原则

### 2.1 核心原则
1. **先验证认知价值，不先追求平台化**
2. **所有产物优先视为可重建快照**
3. **读路径优先简单稳定**
4. **内部复杂度低于展示价值优先**
5. **保留未来升级到数据库/队列的抽象边界**

### 2.2 为什么轻量化
当前系统存储的主要不是业务真相，而是派生结果：

- graph snapshot
- change analysis
- verification summary
- overview snapshot

这些数据都可以从仓库和外部工具重新生成，因此 MVP 阶段不需要重型存储系统。

---

## 3. 总体架构

```text
Frontend Web App
        │
        ▼
FastAPI Overview Server
   ├─ Graph Adapter
   ├─ Change Impact Adapter
   ├─ Verification Adapter
   ├─ Overview Inference
   ├─ In-memory Cache
   ├─ In-memory Job Manager
   └─ File Snapshot Store
        │
        ├─ CodeGraphContext
        ├─ code-review-graph
        └─ repo / CI artifacts
```

### 3.1 组件说明

#### A. Frontend Web App
负责展示：
- Project Summary
- Capability Map
- Core User Journeys
- System Architecture
- Recent AI Change Highlights
- Verification Status

#### B. FastAPI Overview Server
对前端暴露统一 API，并协调各适配器和推断服务。

#### C. Graph Adapter
对接 CodeGraphContext，获取：
- modules
- symbols
- routes
- dependencies
- data_objects
- integrations

#### D. Change Impact Adapter
对接 code-review-graph，获取：
- changed_files
- changed_symbols
- changed_modules
- blast_radius
- minimal_review_set
- risk_score

#### E. Verification Adapter
聚合 CI / unit test / integration test / scenario replay 结果。

#### F. Overview Inference
将 graph、change、verification 融合为首页所需 JSON。

#### G. File Snapshot Store
负责将所有快照落为本地 JSON 文件。

#### H. In-memory Cache
缓存最近 overview 结果，提升读取性能。

#### I. In-memory Job Manager
管理 rebuild 任务状态，支持轮询和 SSE。

---

## 4. 目录结构设计

建议本地目录如下：

```text
data/
  repos/
    {repo_key}/
      meta.json
      latest.json
      snapshots/
        {workspace_snapshot_id}/
          graph_snapshot.json
          change_analysis.json
          verification.json
          overview.json
          capability_map.json
          journeys.json
          architecture.json
      jobs/
        {job_id}.json
      logs/
        rebuild.log
```

### 4.1 文件说明

#### `meta.json`
保存仓库元信息。

示例：
```json
{
  "repo_key": "shop-agent-demo",
  "name": "shop-agent-demo",
  "default_branch": "main",
  "repo_path": "/workspace/repos/shop-agent-demo"
}
```

#### `latest.json`
指向最近可用快照。

示例：
```json
{
  "base_commit_sha": "def456",
  "workspace_snapshot_id": "ws_20260406_a1b2c3",
  "has_pending_changes": true,
  "latest_overview_file": "snapshots/ws_20260406_a1b2c3/overview.json",
  "updated_at": "2026-04-06T10:10:00Z"
}
```

#### `graph_snapshot.json`
标准化后的代码图谱快照。

#### `change_analysis.json`
最近变更影响分析结果。

#### `verification.json`
验证聚合结果。

#### `overview.json`
首页完整聚合数据，前端主读这个文件。

#### `job_id.json`
某次 rebuild 的任务状态。

---

## 5. 文件快照存储设计

## 5.1 SnapshotStore 抽象
建议定义统一接口，避免未来迁移困难。

```python
class SnapshotStore:
    def get_latest_overview(self, repo_key: str) -> dict | None: ...
    def get_overview(self, repo_key: str, workspace_snapshot_id: str) -> dict | None: ...
    def save_graph_snapshot(self, repo_key: str, workspace_snapshot_id: str, payload: dict) -> None: ...
    def save_change_analysis(self, repo_key: str, workspace_snapshot_id: str, payload: dict) -> None: ...
    def save_verification(self, repo_key: str, workspace_snapshot_id: str, payload: dict) -> None: ...
    def save_overview(self, repo_key: str, workspace_snapshot_id: str, payload: dict) -> None: ...
    def set_latest(self, repo_key: str, workspace_snapshot_id: str) -> None: ...
```

## 5.2 文件写入策略
所有 JSON 文件写入必须采用：

1. 先写临时文件 `*.tmp`
2. fsync
3. atomic rename 替换正式文件

这样可以避免服务中断时出现半写文件。

## 5.3 快照保留策略
MVP 建议：

- 永远保留 latest
- 最多保留最近 N=10 个工作区快照
- 超过的旧快照可后台清理

---

## 6. 内存缓存设计

## 6.1 缓存目标
减少磁盘读取，提升首页加载速度。

## 6.2 缓存结构
建议进程内维护：

```python
overview_cache: dict[tuple[str, str], dict] = {}
latest_cache: dict[str, dict] = {}
```

### key 说明
- `(repo_key, workspace_snapshot_id)` -> overview payload
- `repo_key` -> latest pointer / latest overview

## 6.3 读路径
读取 overview 时：

1. 先查内存缓存
2. miss 后读 `overview.json`
3. 读到后回填内存缓存
4. 若没有 overview，则返回 `not_ready` 或提示触发 rebuild

## 6.4 写路径
rebuild 成功后：

1. 保存 overview 文件
2. 更新 `latest.json`
3. 更新内存缓存

---

## 7. 任务管理设计

## 7.1 任务模型
不引入 Celery / Redis queue，改用进程内任务状态管理。

```python
class JobState(TypedDict):
    job_id: str
    repo_key: str
    base_commit_sha: str
    workspace_snapshot_id: str
    status: str
    step: str
    progress: int
    message: str
    created_at: str
    updated_at: str
```

## 7.2 任务状态
- `pending`
- `running`
- `success`
- `failed`
- `partial_success`

## 7.3 进程内存储
```python
job_registry: dict[str, JobState] = {}
# 用于防止同一个 repo 并发执行 rebuild（解决并发写冲突风险）
repo_locks: dict[str, asyncio.Lock] = {}
```

## 7.4 文件持久化
每次状态更新时，同步写入：

```text
data/repos/{repo_key}/jobs/{job_id}.json
```

这样即使服务重启，仍可从文件恢复最后状态。

## 7.5 执行方式
`POST /api/overview/rebuild` 后：

- 尝试获取对应 `repo_key` 的 `asyncio.Lock`，若已被占用则立即返回 `REBUILD_ALREADY_RUNNING` 错误
- 创建 job_id
- 注册 job 状态
- 启动 asyncio background task 负责整体流程调度
- **注意**：流程中的 CPU 密集型操作（如图谱生成、差异分析）必须通过 `run_in_executor` 提交到 `ProcessPoolExecutor` 或 `ThreadPoolExecutor` 中执行，以防止阻塞 FastAPI 的主事件循环
- 顺序执行 rebuild 流程
- 每一步更新 job 状态，任务结束或异常时释放 `repo_locks`

---

## 8. 异步任务流

## 8.1 总流程

```text
1. create job
2. capture working tree snapshot
3. build graph snapshot
4. analyze pending change
5. aggregate verification
6. infer overview
7. write snapshot files
8. update latest pointer
9. mark job success / partial_success
```

## 8.2 详细步骤

### Step 1: create job
输入：
- repo_key
- base_commit_sha（默认 `HEAD`）

输出：
- job_id
- 初始状态文件

### Step 2: capture working tree snapshot
动作：
- 读取当前 Git 工作区状态
- 收集 staged / unstaged diff
- 按规则纳入源码类 / 配置类 untracked files
- 生成 `workspace_snapshot_id`

失败处理：
- 若仓库不可读，任务失败
- 若当前无待提交改动，任务结束并返回 `no_pending_changes`

### Step 3: build graph snapshot
动作：
- 调用 Graph Adapter
- 基于当前工作区文件内容获取标准 graph snapshot
- 写入 `graph_snapshot.json`

失败处理：
- 若失败，任务直接失败
- 若已有同工作区快照的旧 graph snapshot，可按配置选择复用

### Step 4: analyze pending change
动作：
- 调用 Change Impact Adapter
- 生成 `change_analysis.json`

失败处理：
- 允许降级
- 后续 overview 继续生成
- job 最终可标记 `partial_success`

### Step 5: aggregate verification
动作：
- 读取与当前工作区最接近的 build/test/scenario 数据
- 生成 `verification.json`

失败处理：
- 返回 `unknown`
- 不阻塞 overview 生成

### Step 6: infer overview
动作：
- 使用 graph/change/verification 统一输入
- 生成 `overview.json`
- 可额外拆出 capability_map / journeys / architecture

### Step 7: write snapshot files
动作：
- 原子写入 JSON
- 写日志

### Step 8: update latest pointer
动作：
- 写 `latest.json`
- 更新内存缓存

### Step 9: mark job status
动作：
- 成功：`success`
- 若 change/verification 部分失败：`partial_success`

---

## 9. Graph Adapter 设计

## 9.1 输入
- repo_key
- repo_path
- workspace_snapshot_id

## 9.2 输出标准结构

```json
{
  "modules": [],
  "symbols": [],
  "routes": [],
  "dependencies": [],
  "data_objects": [],
  "integrations": []
}
```

## 9.3 字段定义

### modules[]
```json
{
  "module_id": "mod_order_service",
  "name": "order-service",
  "type": "service",
  "files": ["services/order_service.py", "routes/order.py"],
  "linked_symbols": ["sym_create_order"]
}
```

### symbols[]
```json
{
  "symbol_id": "sym_create_order",
  "name": "create_order",
  "kind": "function",
  "module": "order-service",
  "file_path": "services/order_service.py",
  "language": "python"
}
```

### routes[]
```json
{
  "method": "POST",
  "path": "/api/orders",
  "handler": "create_order",
  "module": "order-service"
}
```

### dependencies[]
```json
{
  "from": "mod_api_gateway",
  "to": "mod_order_service",
  "type": "calls"
}
```

### data_objects[]
```json
{
  "name": "Order",
  "type": "entity",
  "used_by": ["order-service", "payment-service"]
}
```

### integrations[]
```json
{
  "name": "Stripe",
  "purpose": "payment",
  "dependency_level": "high"
}
```

---

## 10. Change Impact Adapter 设计

## 10.1 输入
- repo_key
- repo_path
- base_commit_sha（默认 `HEAD`）
- include_staged = true
- include_unstaged = true
- include_untracked = true

## 10.2 输出结构

```json
{
  "base_commit_sha": "def456",
  "workspace_snapshot_id": "ws_20260406_a1b2c3",
  "change_title": "Checkout coupon validation",
  "changed_files": [],
  "changed_symbols": [],
  "changed_modules": [],
  "blast_radius": [],
  "minimal_review_set": [],
  "linked_tests": [],
  "risk_score": 0.72
}
```

## 10.3 字段说明

### changed_files
变更文件列表。

### changed_symbols
变更涉及的核心函数/类/方法。

### changed_modules
变更所属模块。

### blast_radius
潜在受影响区域。

### minimal_review_set
建议 reviewer 最少关注的文件集合。

### linked_tests
关联测试文件。

### risk_score
范围 `[0,1]`，越高风险越大。

---

## 11. Verification Adapter 设计

## 11.1 输入
- repo_key
- workspace_snapshot_id

## 11.2 输出结构

```json
{
  "build": {"status": "passed"},
  "unit_tests": {"passed": 124, "total": 124},
  "integration_tests": {"passed": 11, "total": 12},
  "scenario_replay": {"status": "partial"},
  "critical_paths": [
    {"name": "Login", "status": "verified"},
    {"name": "Checkout", "status": "warning"}
  ],
  "unverified_areas": ["Expired coupon edge case"]
}
```

## 11.3 降级规则
若某部分数据不可用：

- 缺失 build -> `build.status = unknown`
- 缺失 integration -> `integration_tests.status = unknown`
- 缺失 scenario replay -> `scenario_replay.status = unknown`

---

## 12. Overview Inference 设计

## 12.1 输入归一化
Overview Inference 不直接依赖外部工具原始响应，而依赖统一中间结构：

```json
{
  "repo": {},
  "workspace": {},
  "graph": {},
  "change": {},
  "verification": {}
}
```

## 12.2 输出结构
首页统一输出：

```json
{
  "project_summary": {},
  "capability_map": [],
  "journeys": [],
  "architecture_overview": {},
  "recent_ai_changes": [],
  "verification_status": {}
}
```

## 12.3 Summary inference
根据：
- routes
- modules
- data_objects
- integrations
- journeys

生成：
- what_this_app_seems_to_do
- primary_users
- core_flow
- architecture_pattern
- recent_ai_focus
- confidence

## 12.4 Capability inference
启发式规则：

- route prefix 聚类
- module 名称关键词
- data object 聚类
- integration 标签
- UI surface（若有）

输出字段：
- capability_key
- name
- role_visibility
- status
- linked_modules
- entry_surface
- confidence

## 12.5 Journey inference
根据：
- routes
- tests/scenario naming
- service chain
- known action dictionary

约束：
- MVP 最多输出 3 条主路径
- 每条路径 4~8 个 steps

## 12.6 Architecture simplification
将全量 graph 收敛成首页节点图：

- frontend
- gateway
- service
- database
- cache
- queue
- external

节点数建议控制在 5~20 个。

## 12.7 Change overlay mapping
将 change analysis 映射到 capability / journey / module：

1. 优先用 changed_modules 命中 capability.linked_modules
2. 次级用 blast_radius 命中 journey steps
3. 再次用 changed_symbols 命中 entry points
4. 命不中则标记 unknown_area

---

## 13. 对前端 API 设计

## 13.1 GET /api/overview
用途：加载首页完整数据。

### Query
- `repo_key` required
- `workspace_snapshot_id` optional
- `use_cache` optional, default true

### Response
```json
{
  "repo": {
    "repo_key": "shop-agent-demo",
    "name": "shop-agent-demo",
    "default_branch": "main"
  },
  "snapshot": {
    "base_commit_sha": "def456",
    "workspace_snapshot_id": "ws_20260406_a1b2c3",
    "has_pending_changes": true,
    "status": "ready",
    "generated_at": "2026-04-06T10:10:00Z"
  },
  "project_summary": {},
  "capability_map": [],
  "journeys": [],
  "architecture_overview": {
    "nodes": [],
    "edges": []
  },
  "recent_ai_changes": [],
  "verification_status": {},
  "warnings": []
}
```

---

## 13.2 GET /api/capabilities/{capability_key}
用途：能力详情抽屉。

### Response
```json
{
  "capability": {},
  "linked_journeys": [],
  "recent_changes": [],
  "verification_signals": {},
  "suggested_actions": []
}
```

---

## 13.3 GET /api/changes/latest
用途：当前待提交 change 明细。

### Response
```json
{
  "change_id": "chg_20260406_001",
  "title": "Checkout coupon validation",
  "summary": "Added coupon validation before order creation.",
  "changed_files": [],
  "changed_symbols": [],
  "changed_modules": [],
  "blast_radius": [],
  "minimal_review_set": [],
  "affected_capability": "cap_checkout",
  "affected_journeys": [],
  "change_types": [],
  "risk_score": 0.72
}
```

---

## 13.4 GET /api/verification
用途：验证详情。

### Response
```json
{
  "build": {},
  "unit_tests": {},
  "integration_tests": {},
  "scenario_replay": {},
  "critical_paths": [],
  "unverified_areas": []
}
```

---

## 13.5 POST /api/overview/rebuild
用途：触发 rebuild。

### Request
```json
{
  "repo_key": "shop-agent-demo",
  "base_commit_sha": "def456",
  "include_untracked": true
}
```

### Response
```json
{
  "job_id": "job_001",
  "status": "pending"
}
```

---

## 13.6 GET /api/jobs/{job_id}
用途：轮询任务状态。

### Response
```json
{
  "job_id": "job_001",
  "repo_key": "shop-agent-demo",
  "base_commit_sha": "def456",
  "workspace_snapshot_id": "ws_20260406_a1b2c3",
  "status": "running",
  "step": "analyze_pending_change",
  "progress": 80,
  "message": "Analyzing uncommitted diff",
  "created_at": "2026-04-06T10:00:00Z",
  "updated_at": "2026-04-06T10:00:20Z"
}
```

---

## 13.7 GET /api/jobs/{job_id}/stream
用途：SSE 订阅任务进度。

### 事件格式
```text
event: job_progress
data: {"job_id":"job_001","status":"running","step":"analyze_pending_change","progress":60}
```

---

## 14. 文件 JSON Schema 建议

## 14.1 overview.json
建议字段：

```json
{
  "repo": {},
  "snapshot": {},
  "project_summary": {},
  "capability_map": [],
  "journeys": [],
  "architecture_overview": {
    "nodes": [],
    "edges": []
  },
  "recent_ai_changes": [],
  "verification_status": {},
  "warnings": []
}
```

## 14.2 job.json
```json
{
  "job_id": "job_001",
  "repo_key": "shop-agent-demo",
  "base_commit_sha": "def456",
  "workspace_snapshot_id": "ws_20260406_a1b2c3",
  "status": "running",
  "step": "aggregate_verification",
  "progress": 60,
  "message": "Collecting integration test results",
  "created_at": "2026-04-06T10:00:00Z",
  "updated_at": "2026-04-06T10:00:12Z"
}
```

---

## 15. 错误处理与降级

## 15.1 API 错误码
- `OVERVIEW_NOT_READY`
- `REPO_NOT_FOUND`
- `GRAPH_SNAPSHOT_MISSING`
- `CHANGE_ANALYSIS_UNAVAILABLE`
- `VERIFICATION_UNAVAILABLE`
- `JOB_NOT_FOUND`
- `REBUILD_ALREADY_RUNNING`
- `NO_PENDING_CHANGES`

## 15.2 降级规则

### 场景 A：graph snapshot 缺失
- overview 无法新生成
- 若存在旧 overview，则返回旧 overview + warning
- 若没有旧 overview，则返回 `OVERVIEW_NOT_READY`

### 场景 B：change analysis 失败
- `recent_ai_changes` 返回 partial / unknown
- 其余 overview 正常展示

### 场景 B2：当前无待提交改动
- `recent_ai_changes` 返回空数组
- `snapshot.has_pending_changes = false`
- 返回业务状态 `NO_PENDING_CHANGES`
- 其余 overview 仍可展示当前全貌

### 场景 C：verification 失败
- `verification_status` 标记 unknown
- 其余 overview 正常展示

### 场景 D：overview inference 部分失败
- 返回 partial snapshot
- warnings 写明缺失模块

---

## 16. 可观测性

## 16.1 日志字段
每次请求 / rebuild 应记录：

- request_id
- repo_key
- base_commit_sha
- workspace_snapshot_id
- job_id
- step
- duration_ms
- status
- error_code

## 16.2 指标
- `overview_api_latency_ms`
- `overview_cache_hit_ratio`
- `overview_rebuild_duration_ms`
- `graph_snapshot_build_duration_ms`
- `change_analysis_duration_ms`
- `verification_aggregate_duration_ms`
- `overview_partial_rate`
- `overview_failure_rate`

---

## 17. 部署建议

## 17.1 MVP 部署形态
- 单个 FastAPI 服务（**必须限制为单 Worker 模式运行**，例如 `uvicorn main:app --workers 1`。由于依赖了进程内内存状态，多 Worker 会导致任务状态混乱与无法寻址 Job）
- 单机文件目录
- 本地 Redis/DB 都不需要
- 外接 CodeGraphContext / code-review-graph

## 17.2 目录建议
```text
backend/
  app/
    api/
    services/
      graph_adapter/
      change_impact/
      verification/
      overview_inference/
      snapshot_store/
      jobs/
    models/
    schemas/
    utils/
data/
  repos/
```

---

## 18. 研发顺序建议

### Phase 1：最小打通
- 定义 `overview.json`、`job.json` 结构
- 实现 File Snapshot Store
- 实现 `GET /api/overview`
- 实现 `POST /api/overview/rebuild`
- 实现 `GET /api/jobs/{job_id}`

### Phase 2：接外部能力
- 接通 CodeGraphContext
- 接通 code-review-graph
- 接最小 verification 数据源

### Phase 3：做 inference
- summary inference
- capability inference
- journey inference
- architecture simplification
- change overlay mapping

### Phase 4：前端联动
- capability 点击联动
- change 高亮联动
- verification warning 联动
- SSE 任务进度

---

## 19. MVP 验收标准

### 功能
- 能针对单仓库生成 overview.json
- 能展示首页 6 大模块
- 能显示当前待提交 AI change 的影响范围
- 能显示 verification 状态

### 稳定性
- 任一子步骤失败时可合理降级
- overview 文件写入不损坏
- 服务重启后仍可读取已有 snapshot

### 演示价值
- 用户 1 分钟内能说出应用在做什么
- reviewer 能定位当前待提交的 AI 改了哪一块
- 能明确看到当前是否存在 warning / unknown

---

## 20. 未来升级路径
当前轻量方案保留了升级空间，未来可替换：

- File Snapshot Store -> Postgres + Object Store
- In-memory Cache -> Redis
- In-memory Job Manager -> Celery / Queue
- 单机 rebuild -> 多 worker 分布式执行

因此当前方案不是推倒重来，而是一个合理的 MVP 收敛版本。

---

## 21. 结论
这版轻量级技术方案的核心思想是：

- **用文件快照代替数据库**
- **用内存状态代替 Redis**
- **用后台任务代替调度系统**
- **先把工程全貌、当前待提交 AI 改动高亮、验证状态跑通**

MVP 阶段成功标准不是系统多“平台化”，而是让用户快速回答：

1. 这应用在做什么
2. 当前待提交的 AI 改了哪一块
3. 当前是否足够可信
