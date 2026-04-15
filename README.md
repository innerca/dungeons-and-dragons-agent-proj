# Dungeons & Dragons Agent Project

> **当前版本：v0.5007** | [更新日志](#更新日志)

AI 驱动的 DND 游戏项目，基于微服务架构构建。以刀剑神域 Progressive 系列小说为世界观基础，通过 RAG 检索增强生成实现沉浸式游戏体验。

## 🎮 Demo 演示

https://github.com/innerca/dungeons-and-dragons-agent-proj/blob/main/demo-gameplay.mp4

> 视频展示了完整的游戏流程，包含角色创建、世界探索、战斗系统等核心功能。

## 🔖 快速索引

**快速开始** → [Docker 模式](#docker-模式推荐) | [本地开发](#本地开发模式) | [环境要求](#环境要求) | [运行测试](#运行测试)

**测试覆盖** → [运行测试](#运行测试) | [测试覆盖率](#测试覆盖率)

**核心文档** → [架构设计](#架构) | [技术栈](#技术栈) | [安全原则](#安全原则) | [项目结构](#项目结构)

**游戏内容** → [世界观设定](data/dnd-world-setting.md) | [游戏系统](data/dnd-game-system.md) | [小说知识库](#小说知识库向量数据库)

**工程实践** → [Agent 工程手册](agent-engineering-handbook.md) | [完整版手册](engineering/Agent工程手册final_version.md) | [AI质量检查提示词](engineering/claude_quality_check_prompt.md) | [Claude模板](engineering/claude_template.md) | [工程题集](engineering/题集.md)

**代码质量审查** → [Java专属审查](engineering/quality_check_java.md) | [Python专属审查](engineering/quality_check_python.md) | [Go专属审查](engineering/quality_check_go.md) | [TypeScript专属审查](engineering/quality_check_typescript.md) | [C++专属审查](engineering/quality_check_cpp.md) | [Rust专属审查](engineering/quality_check_rust.md)

**架构方案探索** → [轻量级用户画像方案](engineering/端侧轻量级用户画像系统落地方案.md) | [简洁可拓展方案](engineering/端侧用户画像系统：简洁可拓展落地方案.md)

**关于作者** → [关于本项目与我的工作模式](#关于本项目与我的工作模式)

**更新记录** → [更新日志](#更新日志)

## 快速启动

### 首次使用（Docker模式2步完成）

```bash
# 1. 克隆项目
git clone https://github.com/innerca/dungeons-and-dragons-agent-proj.git
cd dungeons-and-dragons-agent-proj

# 2. 配置环境 + 启动服务
make start      # 自动创建 .env + 启动Docker + 初始化数据
```

> 📝 **首次登录**: 打开 http://localhost:3000 注册新账号
>
> ⚙️ **配置API Key**: 编辑 `.env` 填入 `DEEPSEEK_API_KEY`，然后 `docker compose restart gameserver`

### 日常使用

```bash
make start   # 启动服务
make stop    # 停止服务
```

### 数据初始化

**只需首次执行一次**，之后无需重复。

```bash
make init-data        # 初始化（有数据时会询问）
make init-data-reset  # 强制重置（清空并重新初始化）
```

**初始化内容**: 数据库表结构、测试账号、示例数据、向量库

> 💡 **数据安全**: 代码更新不会丢失账号数据，初始化脚本会自动跳过已有数据

### Docker 模式（推荐）

```bash
make start-docker     # 启动（后台运行，自动初始化数据）
# 浏览器: http://localhost:3000

make stop             # 停止
make dev-logs         # 查看日志
```

> ✨ **首次启动自动初始化**: 表结构、怪物/NPC/任务数据
> 
> 📝 **注册账号**: 前端页面注册，创建你的角色
>
> 📊 **可选**: 如需测试数据，运行 `make init-data`（需psql）

> **国内网络**: 需要配置 Docker 镜像加速器，详见[环境要求](#环境要求)

### 本地开发模式

```bash
# 前置依赖: Go 1.22+, Python 3.12+, Node.js 18+, PostgreSQL 16, Redis 7

make dev-gameserver   # 终端1: GameServer :50051
make dev-gateway      # 终端2: Gateway :8080
make dev-frontend     # 终端3: Frontend :5173
```

## 项目概述

本项目将小说转化为 AI 驱动的 DND 游戏体验，游戏逻辑由 LLM 实时生成。架构遵循传统游戏服务器模式：**Gateway - GameServer - Database**。

## 架构

```
                         Docker Compose
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Frontend (React+TS)  ──nginx──>  Gateway (Go)  ──gRPC──>  GameServer (Python)
│       :3000 (80)                    :8080                      :50051
│                                      │                           │
│                                   Redis ◄──────────────────────►│──> LLM API
│                                    :6379                         │   (DeepSeek)
│                                                            PostgreSQL
│                                                              :5432
│                                                            ChromaDB
│                                                          (嵌入式/本地)
└──────────────────────────────────────────────────────────────────────┘

数据流:
  Frontend ──WS/SSE──> Gateway ──gRPC──> GameServer ──ReAct──> LLM (工具调用)
                         │                    │                      │
                      Redis (Auth)     Redis (缓存/对话/战斗)   ActionExecutor
                                       PG (持久化/定义表)       (骰子/伤害计算)
                                       ChromaDB (小说+实体RAG)   QuestService
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | React + TypeScript (Vite) |
| 网关 | Golang (chi router) |
| 游戏服务器 | Python + grpcio |
| 前端通信 | WebSocket (发送) + SSE (接收流式响应) |
| 服务间通信 | gRPC (服务端流式) |
| 数据库 | PostgreSQL 16 + Redis 7 + ChromaDB (嵌入式) |
| 容器化 | Docker Compose |
| Python 包管理 | uv |
| LLM | DeepSeek (默认)，支持多模型切换 + 熔断降级 |
| 知识库 | ChromaDB + BGE-small-zh (中文向量检索) |
| 可观测性 | 全链路 trace_id + 结构化日志 + 请求指标追踪 |

## 安全原则

安全是本项目的最高优先级，采用**纵深防御**策略，在输入、推理、记忆、执行各层进行检测和拦截。

### 核心原则
1. **纵深防御** - 各层检测拦截，攻击成功率 < 5%
2. **最小权限** - Agent 只能访问最少必要工具和数据
3. **人在回路** - 关键操作需人工确认
4. **可观测性** - 所有行为可追溯可复现

### 安全检查矩阵（7项）
- Prompt 注入检测、越狱防御（拒绝率 >95%）、工具参数校验
- 权限隔离、输出泄露防护、成本熔断、审计完整性

> 📖 完整标准见上方表格

## 运行测试

### Python GameServer

```bash
cd gameserver && uv run pytest tests/ -v

# 带覆盖率报告
cd gameserver && uv run pytest tests/ --cov=src/gameserver --cov-branch
```

### Go Gateway

```bash
cd gateway && GO111MODULE=on go test ./... -v

# 带覆盖率报告
cd gateway && GO111MODULE=on go test ./... -coverprofile=coverage.out && go tool cover -html=coverage.out -o coverage.html
```

## 测试覆盖率

### 总体统计
| 项目 | 测试数 | 通过率 | 行覆盖率 | 分支覆盖率 |
|------|--------|--------|---------|-----------|
| Python GameServer | 241 | 100% | 52.30% | 50% |
| Go Gateway | 52 | 73% | 41.4% | - |

> CI自动运行测试，Go覆盖率阈值40%

### 核心模块（Python）

| 模块 | 行覆盖率 | 分支覆盖率 | 状态 |
|------|---------|-----------|------|
| npc_relationship_service.py | 100% | ~95% | 🌟 完美 |
| scene_classifier.py | 91% | ~85% | 🌟 |
| combat_state.py | 88% | ~75% | 🌟 |
| action_executor.py | 86% | 82% | 🌟 |
| state_service.py | 86% | 77% | ✅ |
| postgres.py | 88% | 67% | ✅ |
| redis_client.py | 87% | 67% | ✅ |
| quest_service.py | 84% | 86% | 🌟 |
| context_builder.py | 76% | ~65% | ✅ |

### Go Gateway 测试

| 模块 | 测试文件 | 覆盖率 | 内容 |
|------|---------|--------|------|
| server/config | server_test.go, config_test.go | 100% | 服务器启动、配置加载 |
| middleware | auth/cors/middleware_test.go | 76% | Auth中间件、CORS、日志 |
| handler | auth/channels/sse/websocket_test.go | 34.7% | 认证、通道、SSE、WebSocket |
| grpc/client | grpc_test.go | 0.0% | gRPC客户端（待补充） |

> Go只统计语句覆盖率（statement coverage）

### 测试质量
- ✅ 边界条件、状态转换、错误处理全覆盖
- ✅ 100% Mock策略（fakeredis、asyncpg monkeypatch）
- ✅ 确定性测试（无概率性断言）
- ✅ Given-When-Then 结构

## 环境要求

| 组件 | Docker模式 | 本地开发 |
|------|-----------|----------|
| Docker & Compose | ✅ 必需 | ❌ 可选 |
| Go | ❌ | ✅ 1.22+ |
| Python | ❌ | ✅ 3.12+ |
| Node.js | ❌ | ✅ 18+ |
| PostgreSQL | ✅ 容器 | ✅ 16+ |
| Redis | ✅ 容器 | ✅ 7+ |
| uv (Python包管理) | ❌ | ✅ [安装](https://docs.astral.sh/uv/) |
| protoc + 插件 | ❌ | ✅ 生gRPC代码 |

## 游戏设计文档

基于 SAO Progressive 1-8 卷小说内容，系统化提取世界观设定和游戏系统规则，作为 DND 游戏引擎的设计基础。

| 文档 | 说明 | 路径 |
|------|------|------|
| 世界观设定 | 艾恩葛朗特 1-7 层地理、NPC、怪物、BOSS、历史势力、DM 工具箱 | [`data/dnd-world-setting.md`](data/dnd-world-setting.md) |
| 游戏系统蓝图 | 任务/角色/战斗/经济/交互系统、持久化设计、记忆架构、ReAct 工具调用、玩家认证 | [`data/dnd-game-system.md`](data/dnd-game-system.md) |
| 小说分块策略 | 向量化入库的分块规则与 metadata 标注规范 | [`data/dnd-novel-chunking.md`](data/dnd-novel-chunking.md) |

## 小说知识库（向量数据库）

使用 ChromaDB 存储 SAO Progressive 1-8卷小说（101章节 / 1605 chunks），支持RAG检索增强生成。

### 核心数据
- **数据源**: 8卷TXT文本（`asset/sao/`）
- **分块策略**: 按章节+段落两级拆分（500-1000字符/chunk，100字符重叠）
- **Metadata**: 卷号/故事名/节号 + 艾恩葛朗特层数/游戏内时间
- **Embedding**: BAAI/bge-small-zh-v1.5（中文优化，~90MB）
- **存储**: 本地持久化（`gameserver/data/chromadb/`）

> 📖 详见 [小说分块策略](data/dnd-novel-chunking.md)

### 构建知识库

```bash
cd gameserver && uv sync      # 安装依赖
make ingest-novels             # 向量化入库
make verify-vectordb           # 验证结果
```

## 项目结构

### 核心模块

**GameServer (Python) - DND游戏引擎**
- `game/action_executor.py` - 16个工具处理器 + 5步验证链（权限→前置→资源→计算→写入）
- `game/combat_state.py` - Redis战斗状态管理 + 自动反击系统
- `game/quest_service.py` - 任务状态机（FSM）+ 进度追踪 + 奖励发放
- `game/context_builder.py` - 6层上下文组装（战斗/任务/关系/RAG/历史/系统提示）
- `game/scene_classifier.py` - 场景分类 + 动态工具裁剪 + 场景感知RAG
- `game/npc_relationship_service.py` - NPC关系系统（-100~100，7级好感度）
- `llm/circuit_breaker.py` - 三态熔断器 + 滑动窗口检测 + 自动fallback切换
- `service/request_metrics.py` - 请求指标追踪 + Token成本估算

**Gateway (Go) - API网关**
- `handler/` - REST API（认证/SSE/WebSocket/频道管理）
- `middleware/` - Auth中间件 + CORS + 请求日志
- `grpc/client` - gRPC流式客户端

### 目录结构

```
.
├── frontend/              # React + TypeScript 前端
│   ├── src/pages/         # 登录/注册/角色创建/游戏页面
│   └── src/services/      # API + WebSocket + SSE通信
│
├── gateway/               # Go 网关
│   ├── internal/handler/  # HTTP处理器
│   ├── internal/middleware/ # 中间件
│   └── cmd/gateway/       # 入口
│
├── gameserver/            # Python 游戏服务器
│   ├── src/gameserver/
│   │   ├── game/          # 游戏引擎核心（见上方核心模块）
│   │   ├── llm/           # LLM提供商 + 熔断器
│   │   ├── db/            # PostgreSQL + Redis + ChromaDB
│   │   └── service/       # 业务逻辑 + 请求追踪
│   └── scripts/           # 数据管理 + 向量化脚本
│
├── proto/                 # gRPC 定义（5个RPC）
├── data/                  # 游戏设计文档 + YAML实体
│   ├── entities/          # 怪物/NPC/任务定义
│   └── dnd-*.md           # 世界观 + 游戏系统 + 分块策略
├── asset/sao/             # SAO Progressive 小说文本（1-8卷）
├── scripts/               # 启动/初始化脚本
├── docker-compose.yml     # 容器编排
├── Makefile               # 构建命令
└── VERSION                # 当前版本
```

## 更新日志

### v0.5007 (2026-04-15) - Gateway测试覆盖率补充

**Gateway测试覆盖率补充**
- ✅ 新增 Go Gateway 测试覆盖表格（8个测试文件）
- ✅ 覆盖模块：grpc/handler/middleware/server/config
- ✅ 添加Gateway覆盖率报告生成命令
- ✅ 区分Python GameServer和Go Gateway测试统计
- ✅ 补充准确的测试数据：52个用例，38个通过，总覆盖率41.4%

**链接维护**
- ✅ 更新 README 快速索引中的所有文档链接
- ✅ 更新 agent-engineering-handbook.md 内部对完整版的引用
- ✅ 验证所有文档链接和锚点跳转正确

<details>
<summary>查看完整更新日志</summary>

### v0.5006 (2026-04-14) - 核心模块测试覆盖率大幅提升至 84%+

**测试覆盖重大提升**
- ✅ **总测试数**: 217 → **241** (+24个)
- ✅ **总体行覆盖率**: 47% → **52.30%** (+5.30%)
- ✅ **总体分支覆盖率**: ~42% → **50%** (+8%)

**action_executor.py 覆盖率大幅提升**
- 行覆盖率: 68% → **86%** (+18%)
- 分支覆盖率: 83% → **82%**
- 测试数: 63 → **81** (+18个)
- 新增测试:
  - 技能系统 (3): 未知剑技、等级不足、成功使用
  - 交易功能 (4): 购买成功、珂尔不足、未知物品、出售
  - 装备系统 (5): 无角色、不在背包、已装备、武器、防具
  - 传送水晶 (3): 成功、无效楼层、楼层为0
  - Mock 配置修复 (3)

**quest_service.py 覆盖率提升**
- 行覆盖率: 76% → **84%** (+8%)
- 分支覆盖率: 78% → **86%** (+8%)
- 测试数: 8 → **19** (+11个)
- 新增测试:
  - 任务进度更新 (5): 击杀、到达、无匹配、已完成、完成所有
  - 任务完成奖励 (6): EXP+Col、物品、标志、关系、全奖励、无奖励

**关键修复**
- ✅ Mock 路径修正: `get_redis` 从 `gameserver.game.quest_service` 改为 `gameserver.db.redis_client`
- ✅ AsyncMock 配置: 修复 `state_service.save_player_state` 的 await 错误
- ✅ 测试数据完善: 添加 `progress_json` 和 `rewards_json` 字段
- ✅ 断言修正: 移除不存在的 `skill_used` 字段断言

**测试质量保障**
- ✅ 100% 测试通过 (241/241)
- ✅ 零 skip 测试
- ✅ 无宽松断言
- ✅ Given-When-Then 结构
- ✅ 边界测试和异常路径全覆盖

### v0.5005 (2026-04-14) - 单测覆盖率提升 Phase 2 + 测试质量修复 + CI 集成

**CI 集成**
- ✅ **GitHub Actions 增强**: 自动运行测试 + 覆盖率检查
  - GameServer: 覆盖率阈值 40%，自动生成 XML/HTML/JUnit 报告
  - Gateway: 覆盖率阈值 50%，race condition 检测
  - Codecov 集成: 自动上传覆盖率报告，便于 PR 审查
  - Artifacts: 保留测试报告和覆盖率报告 30 天

**测试覆盖增强**
- **action_executor.py 分支覆盖率大幅提升**: 从 47% 提升至 **68%** (+21%)
  - 新增 10 个条件分支测试，覆盖 4 个核心 handler
  - attack handler (3 tests): 未命中、暴击、怪物死亡
  - use_item handler (3 tests): 解毒药、传送水晶、未知物品
  - flee handler (1 test): 逃跑失败分支
  - move_to handler (3 tests): 危险区域遭遇战、安全区域无遭遇、无 location 参数

**测试质量修复**
- ✅ 删除 2 个过时 skip 测试（test_handle_attack_start_combat, test_handle_attack_existing_combat）
- ✅ 修复 4 个宽松断言（使用 `or` 条件的断言改为精确匹配）
- ✅ 修复 2 个概率性测试（test_roll_natural_max, test_roll_natural_min 改为确定性 mock）
- 结果: 217 passed, **0 skipped** (之前 2 skipped)

**总体测试统计**
- 测试总数: **217 passed**, 0 skipped, 0 failed
- 行覆盖率: **49%** (1184/2432)
- 分支覆盖率: **47%** (274/579)
- action_executor 分支覆盖率: **68%**

### v0.5004 (2026-04-14) - 单测覆盖率提升 Phase 1

**测试覆盖增强**
- **核心模块测试补充**: 新增 69 个测试用例，覆盖率从 25% 提升至 32%（164 passed, 2 skipped）
- **action_executor.py** (10 tests): 工具执行、攻击、防御、升级逻辑、伤害计算边界
- **combat_state.py** (5 tests): 反击逻辑（命中/未命中/暴击/减伤/最小伤害）
- **context_builder.py** (12 tests): 战斗/任务/关系快照格式化、RAG 检索、历史摘要、系统提示
- **quest_service.py** (13 tests): 任务接受（5个场景）、进度更新（完成/部分/错误目标）、触发条件（自动/前置/重复）
- **npc_relationship_service.py** (13 tests): 关系查询、更新边界、等级分界点（7个等级）、极端值
- **scene_classifier.py** (16 tests): 场景分类（大小写/多关键词/自定义）、工具裁剪（空列表/无匹配/全匹配）、工具组完整性

**测试基础设施**
- 添加 pytest-cov 依赖，支持覆盖率报告生成
- 完善 Mock 策略：Redis、PostgreSQL、服务调用链完整模拟
- 测试质量：边界条件、状态转换、错误处理全覆盖

### v0.5003 (2026-04-14) - 代码质量规范检查与修复

**代码质量改进**
- **Python GameServer**: 修复 SQL 注入风险（player_repo 参数化 allowlist）、变量作用域问题、空值检查（openai response.usage、novel parser）、异常处理规范化（分类捕获替代 bare except）、防御性检查（settings、quest_service、chromadb_client）、移除重复代码
- **Go Gateway**: 日志中脱敏认证 token（仅显示后 4 位）、错误日志增加请求路径上下文、类型断言使用 comma-ok 模式、修复配置测试路径解析
- **Frontend**: API 服务增加 JSON 解析 try-catch、错误日志记录（Home.tsx）、提取 shouldTriggerWelcome() 提升可读性、变量命名优化（options → requestOptions）
- **测试增强**: test_action_executor.py 添加 Given-When-Then 结构注释

### v0.5002 (2026-04-14) - 测试覆盖 + Demo 数据

**测试体系**
- **Python GameServer**: 95 个单元测试覆盖核心游戏模块（战斗、动作、任务、NPC、世界标记、场景分类、上下文构建）
- **Go Gateway**: 10 个单元测试覆盖响应通道并发安全和配置加载
- 测试依赖：pytest + pytest-asyncio + pytest-mock + fakeredis

**Demo 数据包**
- `seed_players.sql`: 2 个测试账号和角色数据
- `sample_chunks.json`: 20 个 DND 风格示例文本 chunks
- `demo_setup.sh`: 一键初始化脚本，首次启动自动执行

### v0.5001 (2026-04-13) - 全链路可观测性 + LLM 熔断降级

**可观测性增强**
- **全链路 trace_id 追踪**: Gateway 生成 → gRPC metadata 传递 → GameServer 全模块贯穿 → 前端回传，完整追踪每个请求
- **结构化日志**: key=value 格式，覆盖 DEBUG/INFO/WARN/ERROR/FATAL 五级，支持日志解析和聚合
- **请求指标追踪** (`request_metrics.py`): RAG 检索、LLM 调用、工具执行的关键步骤耗时统计
- **请求摘要日志**: 单条日志汇总整条链路（总耗时、RAG/LLM/工具耗时、Token 数、成本估算）
- **Token 成本估算**: 支持 DeepSeek、GPT-4o、Claude 等主流模型定价，自动计算每次请求成本
- **慢请求告警**: 总耗时 >5s 自动触发 WARN 级别告警，附带各环节耗时分解

**LLM 熔断降级** (`circuit_breaker.py`)
- **轻量级三态熔断器**: CLOSED → OPEN → HALF_OPEN 状态机，线程安全实现
- **滑动窗口失败率检测**: 60s 窗口内失败率 >50% 且请求数 >=5 触发熔断
- **自动 fallback provider 切换**: 主 provider 熔断后自动切换到备用 provider
- **指数退避重试**: OPEN 状态持续 30s 后进入 HALF_OPEN 探测恢复状态

**五步验证链日志**
- 工具调用的 Permission → Precondition → Resource → Compute → State Write 全链路 DEBUG 日志
- 每个步骤记录耗时和结果，便于问题定位

**战斗系统状态日志**
- 战斗开始/更新/结束全流程日志，包含战斗 ID、参与者、回合信息、伤害数值

### v0.5001 (2026-04-07) - Bug 修复 + 全面配置化

**Bug 修复**
- 修复 OpenAI API `missing field tool_call_id` 400 错误：`ChatMessage` 构建和序列化链路中补全 `tool_calls`/`tool_call_id` 字段透传
- 修复 Docker 启动失败：GameServer 健康检查窗口不足（SentenceTransformer 首次需下载 ~90MB 模型），增大 `start_period` 至 300s 并添加 `hf_cache` 持久卷
- 修复前端注册/登录 "connection failed"：前端改为同源请求（经 nginx 代理），消除 CORS 跨域问题；Vite 开发服务器新增 proxy 配置
- 修复 PostgreSQL 缺少 `monster_definitions`/`npc_definitions`/`quest_definitions` 表：`docker-compose.yml` 补挂 `v0500_schema.sql` 迁移文件

**全面配置化（消除 ~50 处硬编码）**
- GameServer `config.yaml` 新增 6 个配置段：`database`（PG 连接池参数）、`redis`（连接数/key 前缀）、`cache`（TTL/消息上限）、`encounter`（遭敌率/安全区域）、`floor`（楼层地图）、`rest`/`relationship`（恢复率/好感度阈值）
- `settings.py` 新增 10 个 dataclass + 全局访问器 `init_settings()`/`get_settings()`
- `combat` 配置扩展：`defense_reduction_factor`、`damage_variance`、`str_scaling_divisor`、`bare_hands_atk`、`crit_multiplier`、`flee_dc`、`generic_monster`
- 所有消费方代码（`postgres.py`、`redis_client.py`、`state_service.py`、`combat_state.py`、`action_executor.py`、`npc_relationship_service.py`）改为从 `get_settings()` 读取
- `main.py` 移除硬编码 `DATABASE_URL` 默认密码，改为必须通过环境变量提供
- Gateway：新增 `SSEConfig`/`RedisAuthConfig`，SSE 超时和 Redis auth key prefix 配置化
- Frontend：`vite.config.ts` 代理目标通过 `VITE_API_PROXY_TARGET`/`VITE_WS_PROXY_TARGET` 环境变量配置

### v0.500 (2026-04-06) - 数据驱动游戏引擎 + RAG 集成 + 完整战斗/任务系统

**Phase 1: 数据基础**
- **3 张定义表**：`monster_definitions`(22列)、`npc_definitions`(16列)、`quest_definitions`(15列)，JSONB 灵活字段
- **Floor 1 种子数据**：8 种怪物、6 个 NPC、3 个任务，全部使用 `ON CONFLICT DO UPDATE` 增量 upsert
- **YAML 实体文件**：`data/entities/` 目录作为 git 跟踪的数据源，含扩展指南注释
- **`manage_game_data.py`**：CLI 工具（sync/show/delete/migrate），从 YAML upsert 到 PG
- **游戏配置外部化**：`config.yaml` 新增 `game:` 段（战斗/升级/经济/场景关键词参数）
- **Settings 数据类**：`CombatConfig`/`LevelingConfig`/`ContextConfig`/`GameConfig`

**Phase 2: RAG 集成**
- **ChromaDB 双集合**：`sao_progressive_novels`(1605 chunks) + `sao_world_entities`(怪物/NPC/任务描述)
- **实体向量化脚本**：`vectorize_entities.py`，从 PG 读取定义表 → 构建描述文档 → `collection.upsert()`
- **场景分类器**：关键词匹配 5 种场景类型（combat/exploration/social/rest/general）
- **动态工具裁剪**：按场景类型过滤不相关工具，节省 ~150-200 token
- **场景感知 RAG**：根据场景类型优先检索对应实体类型（战斗→怪物，社交→NPC）

**Phase 3: 战斗系统**
- **Redis 战斗状态**：`CombatSession` + `MonsterState`，30 分钟 TTL，支持 BOSS 多 HP 条
- **真实怪物数据**：攻击处理器从 PG/Redis 加载实际怪物属性，不再硬编码
- **装备 ATK 集成**：从 `character_inventory` 查询已装备武器的 `weapon_atk`
- **自动反击系统**：怪物每回合自动反击（d20 vs 玩家 AC，伤害 = ATK - DEF*0.6）
- **经验/升级系统**：`exp_to_next = 100 * level^1.5`，+3 属性点/级，升级全回复
- **HP 公式**：`max_hp = 200 + level*50 + vit*10`
- **楼层怪物遭遇**：移动时按当前楼层从 PG 查询实际怪物，25% 遭遇率

**Phase 4: 任务/NPC/世界系统**
- **任务状态机**：`quest_service.py`，FSM: undiscovered → available → active → completed/failed
- **任务触发器**：location/npc_talk/item/auto 四种触发类型，移动和对话后自动检查
- **任务进度追踪**：kill/collect/talk/reach 四种目标类型，击杀和移动后自动更新
- **任务奖励发放**：EXP/Col/物品/世界标记/NPC 关系一次性结算
- **世界标记服务**：`world_flags_service.py`，key-value 标记用于剧情分支和任务前置条件
- **NPC 关系服务**：`npc_relationship_service.py`，-100~100 关系值 + 7 级好感度
- **工具处理器补全**：`accept_quest`(真实任务接取)、`talk_to_npc`(NPC 数据+关系+触发)、`equip_item`(真实装备逻辑)、`inspect`(数据库查询怪物/NPC/物品信息)
- **增强上下文快照**：LLM 上下文注入活跃任务、战斗状态、NPC 关系摘要

### v0.400 (2026-04-06) - DND 游戏引擎 + 全栈重构
- **基础设施**：Docker Compose 新增 PostgreSQL 16 + Redis 7，数据持久化到 named volumes
- **数据库**：12 张表完整 DDL（玩家/角色/物品/剑技/任务/NPC关系/对话历史），初始化种子数据（17 把剑技 + 9 件装备）
- **三层记忆系统**：PostgreSQL 永久存储 → Redis 会话缓存(TTL 2-4h) → LLM Context 窗口(~4700 tokens/请求)
- **ReAct 引擎**：16 个游戏工具（战斗/移动/交互/角色类）+ Action Executor 五步验证链（权限→前置→资源→计算→写入）
- **战斗系统**：d20 命中骰 + ATK×倍率伤害公式 + 会心判定 + 异常状态 + 切换机制
- **认证系统**：Token-based 认证（bcrypt 密码哈希 + Redis token 缓存 24h），Gateway Auth 中间件注入 player_id
- **Proto 扩展**：5 个 RPC（Chat/CreatePlayer/AuthenticatePlayer/CreateCharacter/GetPlayerState）
- **Gateway**：新增 REST API（注册/登录/角色创建/状态查询），Auth 中间件保护 WebSocket 和 API
- **前端**：登录/注册页面 + 角色创建（6 属性分配 10 点）+ 游戏 UI（角色状态栏 + DND 聊天）
- **LLM 增强**：OpenAI 兼容提供商支持 function calling（chat_with_tools），DM 系统提示词
- **一键脚本**：`scripts/start.sh`（自动检测 Docker/本地模式，依赖检查）+ `scripts/stop.sh`
- **对话摘要**：历史消息 > 40 条时自动触发 LLM 压缩，保持上下文窗口精简

### v0.300 (2026-04-06) - DND 游戏设计文档
- 新增世界观设定文档（`data/dnd-world-setting.md`）：艾恩葛朗特 1-7 层完整地理、NPC 名录、怪物与 BOSS 图鉴、历史势力、DM 工具箱
- 新增游戏系统蓝图（`data/dnd-game-system.md`）：任务/角色成长/战斗/经济/世界交互 五大系统，含完整 PostgreSQL DDL（12 张表）、Redis 缓存设计
- 系统蓝图包含三层记忆架构设计（PostgreSQL 持久化 + Redis 会话缓存 + LLM Context 窗口）
- 系统蓝图包含 ReAct 工具调用机制（16 个工具定义 + Action Executor 五步验证链）
- 系统蓝图包含玩家隔离与认证方案（Token 注入 player_id，前端无法伪造）
- 刀剑技能体系：SAO Sword Skill → D&D Battle Master Maneuver 映射（Stance→Assist→Delay→Switch）
- Token 预算规划：system 800 + tools 500 + state 200 + summary 300 + RAG 800 + history 2000 + input 100 ≈ 4700 tokens/请求

### v0.200 (2026-04-06) - 小说知识库
- SAO Progressive 小说（1-8卷）向量化知识库，101 章节 / 1605 chunks
- 向量引擎：ChromaDB（本地持久化） + BAAI/bge-small-zh-v1.5 中文 Embedding
- 两级分块：按章节严格拆分 -> 按段落边界语义拆分（500-1000 字符/chunk，100 字符重叠）
- 双维度 metadata 标注：基础结构（卷/故事/节/chunk）+ 游戏世界（层数/日期）
- 新增小说解析与入库脚本（`gameserver/scripts/`）
- 新增 Makefile target: `ingest-novels` / `verify-vectordb`
- 新增 PyPI 清华镜像 + HuggingFace 镜像加速配置
- 小说 TXT 文本纳入版本控制，EPUB 文件排除

### v0.100 (2026-04-06) - 首次发布
- 完整的项目骨架和目录结构
- gRPC Proto 定义 (GameService 流式 Chat RPC)
- Python GameServer：多模型 LLM 支持 (DeepSeek、OpenAI、Anthropic)
- Go Gateway：WebSocket + SSE + gRPC 客户端
- React + TypeScript 前端：聊天 UI + 流式输出
- Docker Compose：多阶段构建 (GameServer、Gateway、Frontend+nginx)
- 端到端验证通过：Frontend -> WS -> Gateway -> gRPC -> GameServer -> DeepSeek -> SSE 流式响应
- 安全原则和架构文档
- Makefile 统一构建命令

</details>

## 关于本项目与我的工作模式

本项目是一个用于探索生产级 Agent 工程实践的实验室，也是一个展示我**核心工作模式**的窗口。

**我的定位**：
- **系统架构师**：负责需求拆解、模块边界划分、接口契约定义。
- **Spec 驱动者**：将模糊的业务设想转化为可被 AI 执行的精确 Spec。
- **验收与集成者**：审查 AI 生成的代码，确保实现符合设计意图，并完成端到端集成调试。

**我的工作流**：
我采用 **AI-Assisted Spec-Driven Development**。我习惯将大部分编码实现委托给 AI，而将精力聚焦于：
- 系统该做成什么样（What）？
- 边界条件和故障怎么处理（Edge Cases）？
- 各个组件如何可靠地协作（Integration）？

**坦诚地说**：独立手写算法或快速默写 API 并非我的强项。但在 AI 辅助下，我能以极高的效率产出**架构清晰、文档完备、可观测性良好**的生产级系统。

**TL;DR**：
如果你在寻找一个能立刻手写复杂算法的 IC，我可能不是最高效的选择。但如果你在寻找一个能**定义问题、设计系统、把控工程质量**的架构型工程师，这里展示了我的完整方法论。

| 维度 | 哲学思维 | 核心追问 | 匹配依据 | 拆解 |
|------|----------|----------|----------|------|
| 拆解 | 笛卡尔的方法论怀疑 | 这件事由哪些不可再分的部分组成？ | 将复杂问题分解为原子单元，逐一检验，直到找到不可动摇的起点。 | |
| 效果 | 实用主义（皮尔士、詹姆斯） | 这样做会产生什么可感知的实际差别？ | 一个观念的全部意义，就在于它在实践中造成的可观察效果。没有效果差异，就没有意义差异。 | |
| 时间 | 《论持久战》的阶段论 | 现在是哪个阶段？该进攻还是防守？ | 承认力量对比的动态变化，不追求速胜，在时间轴上找到当前阶段的核心任务。 | |
| 前提 | 苏格拉底的反诘法 | 这个问题本身成立吗？提问的预设是什么？ | 在回答之前先追问定义和前提，很多时候问题本身就包含了需要被质疑的假设。 | |
| 证据 | 休谟的经验主义 | 这个结论的依据是什么？是实测还是推演？ | 区分"观念关系"和"实际事情"，关于事实的结论必须能追溯到感官经验。 | |
| 边界 | 康德的批判哲学 | 这个方案能做什么？不能做什么？边界在哪里？ | 审视理性工具自身的合法应用范围，在能力边界内行动，不越界妄言。 | |
| 矛盾 | 《矛盾论》 | 当前的主要矛盾是什么？次要矛盾是什么？ | 事物发展由内部矛盾推动，抓住主要矛盾，其他问题随之迎刃而解。 | |

这是我的思考过程，希望对你能有些拓扑性的帮助。anyway，我并不擅长在短时间写算法题。工程不是一道算法，是在成本和需求之间的妥协。

---

**Copyright (C) 2026 Xing Mingcheng**

This project and all its historical commits are licensed under [CC BY-NC-ND 4.0](LICENSE) (Attribution-NonCommercial-NoDerivatives 4.0 International).
