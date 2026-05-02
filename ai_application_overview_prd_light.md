# 研发版 PRD：whether_commit（轻量版）

## 1. 文档目的
本文件用于指导工程团队按模块拆解并实现 **whether_commit** 的 MVP：协助判断当前代码变更是否应该提交。
该版本为 **轻量级落地版 PRD**，重点是：

- 不引入数据库
- 不引入 Redis
- 不引入任务队列
- 使用单进程服务 + 本地文件快照实现 MVP

与产品版 PRD 相比，本文件更关注：

- 系统边界
- 模块职责
- 页面与接口范围
- 数据产物
- 任务拆解
- 验收标准

---

## 2. 项目定义

### 2.1 一句话定义
一个面向 AI 搭建/修改代码场景的应用全貌与变更影响平台，帮助用户在不读代码的情况下理解：

- 应用在做什么
- 核心能力有哪些
- 主路径是什么
- 当前待提交的 AI 改了哪一块
- 改动影响了什么
- 当前验证状态如何

### 2.2 MVP 范围
MVP 仅交付以下页面与能力：

1. Overview 首页
2. Project Summary
3. Capability Map
4. Core User Journeys
5. System Architecture Overview
6. Recent AI Change Highlights
7. Verification Status

### 2.3 不做内容
MVP 暂不包含：

- 在线编辑代码
- 全量行为回放 UI
- 多仓库聚合
- 用户手工标注写回
- 完整权限系统
- 平台级任务调度系统

### 2.4 “最近 AI 改动”定义
本 PRD 中的“最近 AI 改动”统一指当前 Git 工作区中尚未提交的改动集合。

默认包含：

- staged changes
- unstaged changes
- 未被 `.gitignore` 忽略的源码类 / 配置类 untracked files

默认不包含：

- 已提交到 Git 历史中的旧改动
- `.gitignore` 命中的文件
- 构建产物、缓存文件、日志文件等非源码产物

统一分析基线为 `HEAD + 当前工作区待提交内容`，不再以“最近一次 commit”作为最近 AI 改动的口径。

---

## 3. 产品目标

### 3.1 核心目标
1. 自动生成应用全貌图，让用户快速理解项目是什么
2. 自动识别主要能力、主路径、系统模块与数据/集成关系
3. 将 AI 改动叠加到全貌图上，展示 blast radius 和受影响区域
4. 显示验证状态与未覆盖风险，提升对 AI 改动的信任度

### 3.2 非目标
1. 不替代 IDE 或代码编辑器
2. 不作为通用 CI/CD 平台
3. 不在 V1 直接提供完整运行时重放/在线调试环境
4. 不在 V1 追求完美准确的产品语义理解，允许先做到高价值、可校正的推断

---

## 4. 系统边界与依赖

### 4.1 外部依赖

#### A. CodeGraphContext
用途：全库代码图谱底座  
输入：代码仓库  
输出：

- symbols
- dependencies
- call graph
- module relationships

#### B. code-review-graph
用途：变更影响分析  
输入：

- git diff
- changed files
- changed symbols

输出：

- blast radius
- minimal review set
- risk score

#### C. CI / Test / Scenario Sources
用途：验证信息聚合  
输入：

- build result
- unit test result
- integration test result
- scenario replay result

输出：

- verification summary

### 4.2 本系统自研模块
1. Graph Adapter
2. Change Impact Adapter
3. Verification Adapter
4. Overview Inference
5. File Snapshot Store
6. In-memory Job Manager
7. Overview API Service
8. Frontend Web App

---

## 5. 目标用户与核心场景

### 5.1 用户角色

#### A. AI 应用 Builder / 创业者
关注点：

- 我这套 AI 搭起来的系统现在大概是什么
- 哪里最关键
- 哪里最近被 AI 动过

核心价值：

- 不用读完整代码即可建立整体认知

#### B. Tech Lead / Reviewer
关注点：

- 这次改动影响哪里
- 应该 review 哪些模块
- 风险在哪

核心价值：

- 获取最小 review 集合与受影响范围

#### C. 架构师 / 后端负责人
关注点：

- 改动是否破坏系统边界
- 是否影响核心主路径
- 验证是否充分

核心价值：

- 全貌图 + 模块关系 + 验证视图

#### D. 产品负责人 / 非代码参与者
关注点：

- 系统现在支持哪些能力
- 最近改动对用户路径有什么影响

核心价值：

- 从产品能力和用户路径理解应用

### 5.2 核心使用场景
1. 打开一个主要由 AI 搭建的仓库，快速知道这个应用在做什么
2. 查看当前 git 待提交的 AI 变更影响了哪些能力和主路径
3. 做 code review 前先看最小 review 集合和 blast radius
4. 发布前确认关键能力是否被验证覆盖
5. 新成员接手项目时，先通过总览页建立系统认知

---

## 6. 方案总览

采用分层结构：

### 6.1 底层：CodeGraphContext
负责全库图谱底座，包括：

- symbols
- imports / dependencies
- call graph
- module relationships
- 持续索引与查询接口

### 6.2 中层：code-review-graph
负责变更影响分析，包括：

- blast radius
- minimal review set
- risk score
- change-centric graph updates

### 6.3 上层：自研网页
负责认知与展示层，包括：

- AI Application Overview
- capability map
- user journeys
- system architecture
- AI change overlay
- verification status

---

## 7. 核心产品原则
1. 先看全貌，再看改动
2. 先看能力和主路径，再看代码入口
3. 把代码改动投影为应用变化，而不是停留在 diff
4. 把图谱、影响、验证分层，不把所有逻辑耦合在单一模型输出里
5. 所有自动推断都允许用户校正
6. MVP 阶段优先文件快照方案，不优先平台化基础设施

---

## 8. 信息架构

### 8.1 一级页面
1. Overview 总览
2. Capability 能力地图
3. Journeys 用户路径
4. Architecture 系统结构
5. Changes AI 变更影响
6. Verification 验证状态
7. Code Entry Points 代码入口（后置）

### 8.2 Overview 首页模块
1. Project Summary
2. Product Capability Map
3. Core User Journeys
4. System Architecture Overview
5. Recent AI Change Highlights
6. Verification Status
7. Risk & Unknown Areas（Beta）
8. Capability to Code Entry Points（Beta）

---

## 9. 核心功能需求

## 9.1 Project Summary

### 目标
让用户 5 秒内知道这个应用大概是什么。

### 输入
- 路由结构
- UI surface / 页面信息（若可取）
- 模块命名
- 数据对象
- 外部集成
- 主路径推断结果

### 输出
- What this app seems to do
- Primary users
- Core flow
- Architecture pattern
- Current focus of recent AI work

### 交互
- 展开摘要
- 查看推断依据
- 标记摘要不准确

---

## 9.2 Capability Map

### 目标
将工程映射为一组人类可理解的能力块。

### 输出字段
- Capability name
- Role visibility
- Status
- Linked modules
- Entry surface

### 状态定义
- Stable
- Recently changed
- Partially verified
- Needs review
- Unknown

### 交互
- 点击能力块，联动高亮主路径、架构图、变更卡片
- 进入 capability detail drawer

---

## 9.3 Core User Journeys

### 目标
让用户不看代码也知道应用主干怎么用。

### 输出字段
- Journey name
- Primary actor
- Steps
- Criticality
- Recent impact

### 交互
- 回放这条路径
- 查看受影响步骤
- 查看相关模块
- 查看验证场景

---

## 9.4 System Architecture Overview

### 目标
用简化结构图展示系统大致由哪些层和模块构成。

### 输出节点类型
- Frontend
- Gateway / BFF
- Service
- Database
- Cache
- Queue
- External Integration

### 节点字段
- Module name
- Module type
- Health / state
- Main responsibility
- Linked capabilities

### 交互
- 展开依赖
- 高亮最近变更
- 查看模块详情

---

## 9.5 Recent AI Change Highlights

### 目标
把最近 AI 改动映射到“能力—路径—模块”三层。

### 输出字段
- Change set title
- Change summary
- Changed capability
- Affected journey
- Changed modules
- Change type
- Confidence

### Change type 枚举
- Rule change
- Flow change
- Contract change
- Data write path change
- External integration change
- Verification-only change

### 交互
- 查看完整变更
- 查看 before vs after
- 查看受影响行为
- 查看验证证据
- 若当前无待提交改动，明确展示 empty state

---

## 9.6 Verification Status

### 目标
展示当前系统的可信度，而不仅是“代码存在”。

### 输出字段
- Build
- Unit tests
- Integration tests
- Scenario replay
- Critical paths
- Unverified areas

### 状态等级
- Verified
- Partial
- Warning
- Unknown

### 交互
- 打开验证报告
- 回放失败场景
- 查看未覆盖区域
- 重新运行验证

---

## 9.7 Risk & Unknown Areas（Beta）

### 目标
明确告诉用户哪里理解不足、验证不足、映射不足。

### 输出字段
- Unknown capability / area
- Why it is unclear
- Risk level
- Suggested next action

---

## 9.8 Capability to Code Entry Points（Beta）

### 目标
让技术用户可以从能力块跳到代码落点。

### 表格字段
- Capability
- Main module
- Likely entry points
- Recent changes
- Verification

---

## 10. 轻量级实现约束

### 10.1 不引入
- PostgreSQL
- Redis
- Celery / 队列系统
- DB migration
- 分布式锁

### 10.2 使用方式
- 本地 JSON 快照文件
- 进程内缓存
- 进程内 Job 状态管理
- 后台线程 / asyncio task
- 前端轮询或 SSE 订阅进度

### 10.3 文件目录
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
      jobs/
        {job_id}.json
```

---

## 11. 数据流设计

### 11.1 输入源
1. 仓库当前代码、Git 工作区状态与 HEAD 基线
2. CodeGraphContext 生成的全库图谱
3. code-review-graph 输出的 blast radius / risk score / minimal review set
4. CI / test / scenario replay 结果
5. 用户手工校正信息（后续版本）

### 11.2 处理层
1. Graph ingestion
2. Capability inference
3. Journey inference
4. Architecture simplification
5. Change overlay mapping
6. Verification aggregation

### 11.3 输出层
- overview.json
- graph_snapshot.json
- change_analysis.json
- verification.json
- job.json

---

## 12. 关键推断逻辑

### 12.1 Capability inference（启发式 + LLM 总结）
输入信号：
- route prefixes
- page names
- service/module naming
- data model names
- external integrations
- repeated flow motifs

输出：
- capability candidates
- capability descriptions
- confidence

### 12.2 Journey inference
输入信号：
- routes / UI surfaces
- service chain
- event flows
- tests / scenario naming

输出：
- main user journeys
- step sequence
- criticality

### 12.3 Change overlay mapping
输入：
- changed files / symbols（来自当前待提交 diff）
- blast radius
- minimal review set
- linked modules

输出：
- changed capability
- affected journey
- changed modules
- risk score

### 12.4 Verification aggregation
输入：
- build/test reports
- scenario replay reports
- critical-path assertions

输出：
- per capability status
- per journey status
- global confidence summary

---

## 13. 页面交互规则

### 13.1 Overview 联动原则
点击任一 capability：
- 高亮相关 journey
- 高亮架构图对应模块
- 过滤 change highlights
- 更新 verification 状态视图

点击任一 AI change：
- 高亮 capability
- 高亮受影响 journey step
- 高亮 affected modules
- 提供查看行为差异入口

若当前无待提交改动：
- 展示“当前没有待提交 AI 改动”
- 不复用旧 change highlights 冒充当前变更

点击任一 verification warning：
- 展示相关未验证 capability / journey / module
- 跳转失败场景或未覆盖区域

---

## 14. MVP 范围

### 14.1 必做
1. Project Summary
2. Capability Map
3. Core User Journeys
4. System Architecture Overview
5. Recent AI Change Highlights
6. Verification Status

### 14.2 延后
1. Risk & Unknown Areas
2. Capability to Code Entry Points
3. Why this summary was inferred
4. 深度行为回放
5. 用户校正与持久化

---

## 15. 用户故事

### 15.1 Builder
作为一个主要靠 AI 搭应用的开发者，  
我希望打开项目后先看到一张总览页，  
从而不用读完整代码也能知道这个应用现在在做什么。

### 15.2 Reviewer
作为 code reviewer，  
我希望看到当前待提交的 AI 改动影响了哪些能力、模块和主路径，  
从而快速确定 review 范围。

### 15.3 Tech Lead
作为技术负责人，  
我希望知道关键路径当前是否验证通过、哪些区域仍然未知或有警告，  
从而判断是否适合继续推进或发布。

---

## 16. API 范围（MVP）

### 16.1 必做接口
- `GET /api/overview`
- `POST /api/overview/rebuild`
- `GET /api/jobs/{job_id}`

### 16.2 第二阶段接口
- `GET /api/capabilities/{capability_key}`
- `GET /api/changes/latest`
- `GET /api/verification`
- `GET /api/jobs/{job_id}/stream`

---

## 17. 工程拆解（按 Sprint）

## Sprint 1：基础骨架
### 后端
- 定义 overview / graph / change / verification / job 的 JSON schema
- 实现 File Snapshot Store
- 实现 In-memory Job Manager
- 实现 mock `GET /api/overview`
- 实现 `POST /api/overview/rebuild`
- 实现 `GET /api/jobs/{job_id}`

### 前端
- 搭建 Overview 首页骨架
- 定义全局 layout
- 实现 loading / error / partial 状态

### 验收
- 能用 mock 数据跑通首页展示
- 后端接口定义固定下来

---

## Sprint 2：接外部能力
### 后端
- 接入 CodeGraphContext
- 接入 code-review-graph
- 接入最小 verification 数据源
- 生成 graph_snapshot / change_analysis / verification 文件
- 以当前工作区待提交内容作为 change_analysis 输入

### 前端
- 接入真实 overview API
- 实现 Project Summary
- 实现 Capability Map
- 实现 Core User Journeys
- 实现 System Architecture Overview
- 实现 Recent AI Change Highlights
- 实现 Verification Status

### 验收
- 单仓库能完整展示 6 大模块
- 当前待提交 AI change 能正确高亮 1 个 capability 和相关模块

---

## Sprint 3：联动与稳定性
### 后端
- capability detail API（可选）
- latest change detail API（可选）
- SSE 任务进度（可选）
- rebuild 流程降级与错误处理

### 前端
- capability 点击联动
- change 点击联动
- verification warning 联动
- capability detail drawer（可选）

### 验收
- 页面交互可用于真实项目 review 演示
- 任一模块失败不导致整页失败

---

## 18. 前端组件清单

### 页面级
- `OverviewPage`
- `OverviewHeader`
- `SummaryHeroCard`
- `CapabilityMapCard`
- `JourneyCard`
- `ArchitectureOverviewCard`
- `RecentAIChangesCard`
- `VerificationStatusCard`

### 交互组件
- `CapabilityDetailDrawer`
- `ChangeDetailDrawer`（可后置）
- `VerificationDetailDrawer`（可后置）

### 状态组件
- `CardSkeleton`
- `PartialDataBanner`
- `UnknownStateTag`
- `ConfidenceBadge`

---

## 19. 核心指标

### 19.1 认知效率指标
- 首次打开项目后，用户在 60 秒内说出“应用主要做什么”的比例
- 首次打开项目后，用户在 2 分钟内定位当前待提交 AI 改动所属能力的比例

### 19.2 Review 效率指标
- reviewer 找到 review 范围的时间下降
- reviewer 打开的无关文件数量下降

### 19.3 信任指标
- 用户对“当前验证状态是否清晰”的满意度
- 用户对“当前待提交 AI 改了什么是否清晰”的满意度

### 19.4 产品使用指标
- Overview 页面停留时长
- capability 点击率
- change highlight 点击率
- verification detail 打开率

---

## 20. 风险与挑战

1. 自动推断 capability 和 journey 准确率不稳定
2. 不同技术栈项目的结构差异大
3. 待提交工作区 diff 与产品层映射需要启发式 + 模型协同
4. 过度复杂图谱会降低可读性
5. verification 数据来源不统一
6. 单进程轻量方案并发能力有限
7. rebuild 过程中工作区继续变化会导致快照与页面状态漂移

### 应对策略
- 先做高价值启发式规则
- 明确显示 confidence 和 unknown areas
- 允许用户手工校正（后续）
- V1 只展示简化图而非全量图
- 任务状态落文件，避免服务重启后完全丢失
- 后续如有需要再升级到 DB/Redis/队列

---

## 21. 上线验收清单

### 功能
- [ ] Overview 首页完成
- [ ] 6 大模块输出稳定
- [ ] 能接入真实 CodeGraphContext
- [ ] 能接入真实 code-review-graph
- [ ] 能展示当前待提交 change impact
- [ ] 能展示 verification summary

### 稳定性
- [ ] 异常状态有清晰降级
- [ ] overview 构建可重试
- [ ] 文件写入采用原子替换
- [ ] 服务重启后仍可读取已有 snapshot

### 演示价值
- [ ] 对一个 AI 搭建仓库，用户 1 分钟内能说出系统主要能力
- [ ] reviewer 能快速看到当前待提交 AI change 的影响区域

---

## 22. 建议实现顺序
最优实现顺序：

1. 定义统一 JSON 数据结构
2. 打通 mock overview API
3. 实现 File Snapshot Store
4. 实现 In-memory Job Manager
5. 接入 CodeGraphContext
6. 接入 code-review-graph
7. 做 Overview Inference
8. 接前端真实渲染
9. 做联动和降级稳定性

---

## 23. 结论
MVP 的关键不是做一个完美图谱平台，而是尽快做出：

- 应用全貌
- 当前待提交 AI 改动映射
- 验证状态

也就是先让用户回答三个问题：

1. 这应用大概是干什么的
2. 当前待提交的 AI 改了哪一块
3. 现在靠不靠谱

只要这三点成立，产品就已经具备强演示价值和实际工程价值。
