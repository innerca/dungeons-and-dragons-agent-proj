# Dungeons & Dragons Agent Project

> **当前版本：v0.5001** | [更新日志](#更新日志)

AI 驱动的 DND 游戏项目，基于微服务架构构建。以刀剑神域 Progressive 系列小说为世界观基础，通过 RAG 检索增强生成实现沉浸式游戏体验。

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
| 证据 | 休谟的经验主义 | 这个结论的依据是什么？是实测还是推演？ | 区分“观念关系”和“实际事情”，关于事实的结论必须能追溯到感官经验。 | |
| 边界 | 康德的批判哲学 | 这个方案能做什么？不能做什么？边界在哪里？ | 审视理性工具自身的合法应用范围，在能力边界内行动，不越界妄言。 | |
| 矛盾 | 《矛盾论》 | 当前的主要矛盾是什么？次要矛盾是什么？ | 事物发展由内部矛盾推动，抓住主要矛盾，其他问题随之迎刃而解。 | |

这是我的思考过程，希望对你能有些拓扑性的帮助。anyway，我并不擅长在短时间写算法题。工程不是一道算法，是在成本和需求之间的妥协。

## 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/innerca/dungeons-and-dragons-agent-proj.git
cd dungeons-and-dragons-agent-proj

# 2. 配置环境变量（填入你的 API Key）
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 一键启动（自动检测 Docker / 本地环境）
make start
# 或直接：bash scripts/start.sh

# 4. 一键停止
make stop
```

### 方式一：Docker 一键启动（推荐）

```bash
make start-docker
# 或: make dev
# 浏览器打开 http://localhost:3000

# 停止服务
make stop

# 查看日志
make dev-logs
```

> **国内网络注意：** Docker Hub 在国内可能无法直接访问，需要配置镜像加速器。
> 在 Docker daemon 配置中添加（OrbStack 为 `~/.orbstack/config/docker.json`，Docker Desktop 为 Settings > Docker Engine）：
> ```json
> {
>   "registry-mirrors": [
>     "https://docker.m.daocloud.io",
>     "https://mirror.ccs.tencentyun.com"
>   ]
> }
> ```
> 此外，Dockerfile 中已内置国内加速配置：
> - Gateway: `GOPROXY=https://goproxy.cn,direct`
> - GameServer: PyPI 清华源 `https://pypi.tuna.tsinghua.edu.cn/simple`

### 方式二：本地开发

```bash
# 前置依赖（首次需要）
# - Go 1.22+, Python 3.12+, Node.js 18+, protoc
# - uv: curl -LsSf https://astral.sh/uv/install.sh | sh
# - protoc Go 插件: go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
# - 前端依赖: cd frontend && npm install && cd ..
# - GameServer 依赖: cd gameserver && uv sync && cd ..

# 生成 gRPC 代码（修改 proto 文件后执行）
make proto-gen

# 分别在三个终端启动服务（按此顺序）
make dev-gameserver     # 终端 1: Python GameServer :50051
make dev-gateway        # 终端 2: Go Gateway :8080
make dev-frontend       # 终端 3: React Frontend :5173
# 浏览器打开 http://localhost:5173

# 查看所有可用命令
make help
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
| LLM | DeepSeek (默认)，支持多模型切换 |
| 知识库 | ChromaDB + BGE-small-zh (中文向量检索) |

## 安全原则

安全是本项目的最高优先级，嵌入到每一层架构中。

### 核心原则
1. **纵深防御**: 在输入、推理、记忆、执行各层进行检测和拦截
2. **最小权限**: Agent 只能访问完成任务所需的最少工具和数据
3. **人在回路**: 关键操作需要人工确认
4. **可观测性**: 所有行为可追溯、可复现

### 安全检查矩阵

| 检查项 | 方法 | 通过标准 |
|--------|------|----------|
| Prompt 注入检测 | 通过 Garak、PromptInject 自动化攻击 | 攻击成功率 < 5% |
| 越狱防御 | 测试 50+ 已知越狱模板 | 拒绝率 > 95% |
| 工具参数校验 | 异常类型、SQL 注入、路径穿越 | 工具拒绝执行并记录日志 |
| 权限隔离 | 用户 A 尝试访问用户 B 的数据 | 返回未授权错误 |
| 输出泄露防护 | 回复中随机出现手机号、邮箱 | 脱敏模块检测并遮蔽 |
| 成本熔断 | 模拟超长对话或循环调用 | 达到阈值时终止或上报 |
| 审计完整性 | 检查所有关键事件日志 | 日志完整且防篡改 |

## 环境要求

**Docker 方式（推荐）：**
- Docker & Docker Compose

**本地开发方式：**
- Go 1.22+（确保 `$(go env GOPATH)/bin` 在 PATH 中）
- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/)（Python 包管理）
- protoc（Protocol Buffers 编译器）
- protoc-gen-go, protoc-gen-go-grpc（Go gRPC 代码生成插件）

## 游戏设计文档

基于 SAO Progressive 1-8 卷小说内容，系统化提取世界观设定和游戏系统规则，作为 DND 游戏引擎的设计基础。

| 文档 | 说明 | 路径 |
|------|------|------|
| 世界观设定 | 艾恩葛朗特 1-7 层地理、NPC、怪物、BOSS、历史势力、DM 工具箱 | [`data/dnd-world-setting.md`](data/dnd-world-setting.md) |
| 游戏系统蓝图 | 任务/角色/战斗/经济/交互系统、持久化设计、记忆架构、ReAct 工具调用、玩家认证 | [`data/dnd-game-system.md`](data/dnd-game-system.md) |
| 小说分块策略 | 向量化入库的分块规则与 metadata 标注规范 | [`data/dnd-novel-chunking.md`](data/dnd-novel-chunking.md) |

## 小说知识库（向量数据库）

项目使用 ChromaDB 将刀剑神域 Progressive 系列小说（1-8卷）向量化存储，用于游戏中的 RAG（检索增强生成）。

### 数据源

8 本 SAO Progressive 小说的 TXT 文本，位于 `asset/sao/` 目录。

| 卷 | 故事 | 艾恩葛朗特层数 |
|---|---|---|
| 1 | 无星夜的咏叹调 / 幻眬剑之回旋曲 | 1-2 层 |
| 2 | 黑白协奏曲 | 3 层 |
| 3 | 泡影的船歌 | 4 层 |
| 4 | 阴沉薄暮的诙谐曲 | 5 层 |
| 5-6 | 黄金定律的卡农（上/下）| 6 层 |
| 7-8 | 赤色焦热的狂想曲（上/下）| 7 层 |

入库统计：**101 个章节 / 1605 个 chunks / 8 卷全覆盖**

### 分块策略

- **第一级**：按故事章节（story + section number）严格拆分
- **第二级**：在章节内按段落边界拆分，每 chunk 约 500-1000 字符，相邻 chunk 间保留 100 字符重叠

### 数据标注

每个 chunk 携带两个维度的 metadata：

| 维度 | 字段 | 说明 |
|------|------|------|
| 基础结构 | `volume`, `story_title`, `section_number`, `chunk_index` | 卷号、故事名、节号、chunk 序号 |
| 游戏世界 | `aincrad_layer`, `in_game_date` | 艾恩葛朗特层数、游戏内时间 |

### 向量数据库配置

- 引擎：ChromaDB（本地持久化）
- Embedding 模型：BAAI/bge-small-zh-v1.5（中文优化，~90MB）
- 存储路径：`gameserver/data/chromadb/`（不提交到 git）
- Collection：`sao_progressive_novels`

### 构建知识库

```bash
# 安装依赖（首次）
cd gameserver && uv sync

# 执行向量化入库
make ingest-novels

# 验证入库结果
make verify-vectordb
```

## 项目结构

```
.
├── proto/              # 共享 gRPC 定义 (5 个 RPC)
├── frontend/           # React + TypeScript 前端 (登录/注册/角色创建/游戏)
├── gateway/            # Golang 网关 (Auth 中间件 + REST API)
├── gameserver/         # Python 游戏服务器 (DND 引擎)
│   ├── src/gameserver/
│   │   ├── config/     # 配置加载 (游戏参数/战斗/升级/经济)
│   │   ├── db/         # PostgreSQL + Redis + ChromaDB 连接层
│   │   ├── game/       # 游戏引擎核心
│   │   │   ├── action_executor.py   # 16 工具处理器 + 5 步验证链
│   │   │   ├── combat_state.py      # Redis 战斗状态 + 自动反击
│   │   │   ├── quest_service.py     # 任务状态机 (FSM)
│   │   │   ├── world_flags_service.py    # 世界标记/剧情分支
│   │   │   ├── npc_relationship_service.py # NPC 关系 (-100~100)
│   │   │   ├── scene_classifier.py  # 场景分类 + 工具/RAG 裁剪
│   │   │   ├── context_builder.py   # 6 层上下文组装
│   │   │   └── tools.py             # ReAct 工具定义
│   │   ├── llm/        # LLM 提供商 (DeepSeek/OpenAI/Claude)
│   │   └── service/    # 业务逻辑层
│   └── scripts/        # 数据库初始化/迁移/数据管理/向量化
│       └── migrations/  # SQL 迁移 (v0500_schema.sql)
├── scripts/            # 一键启动/停止脚本 (含环境检测)
├── asset/              # 游戏资源
│   └── sao/            # SAO Progressive 小说文本 (1-8卷)
├── data/               # 游戏设计文档 + 实体数据
│   └── entities/       # YAML 实体定义 (怪物/NPC/任务，git 跟踪)
├── docker-compose.yml  # 容器编排 (PG + Redis + GameServer + Gateway + Frontend)
├── Makefile            # 构建命令
└── VERSION             # 当前版本
```

## 更新日志

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

This project and all its historical commits are licensed under CC BY-NC-ND 4.0.
