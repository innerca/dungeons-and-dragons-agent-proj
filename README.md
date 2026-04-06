# Dungeons & Dragons Agent Project

AI 驱动的 DND 游戏项目，基于微服务架构构建。

## 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/innerca/dungeons-and-dragons-agent-proj.git
cd dungeons-and-dragons-agent-proj

# 2. 配置环境变量（填入你的 API Key）
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 方式一：Docker 一键启动（推荐）

```bash
make dev
# 浏览器打开 http://localhost:3000

# 停止服务
make dev-down

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
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  Frontend (React+TS)  ──nginx──>  Gateway (Go)  ──gRPC──>  GameServer (Python)  -->  LLM API
│       :3000 (80)                    :8080                      :50051              (DeepSeek)
│                                                          │
└──────────────────────────────────────────────────────────┘

本地开发:
  Frontend (:5173)  <--WS/SSE-->  Gateway (:8080)  <--gRPC-->  GameServer (:50051)  -->  LLM API
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | React + TypeScript (Vite) |
| 网关 | Golang (chi router) |
| 游戏服务器 | Python + grpcio |
| 前端通信 | WebSocket (发送) + SSE (接收流式响应) |
| 服务间通信 | gRPC (服务端流式) |
| 数据库 | PostgreSQL + Redis (规划中) |
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

## 小说知识库（向量数据库）

项目使用 ChromaDB 将刀剑神域 Progressive 系列小说（1-8卷）向量化存储，用于游戏中的 RAG（检索增强生成）。

### 数据源

8 本 SAO Progressive 小说的 TXT 文本，位于 `asset/sao/` 目录，总计约 3.7MB、49,000+ 行。

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
├── proto/              # 共享 gRPC 定义
├── frontend/           # React + TypeScript 前端
├── gateway/            # Golang 网关
├── gameserver/         # Python 游戏服务器
│   └── scripts/        # 数据处理脚本 (小说解析、向量化入库)
├── asset/              # 游戏资源
│   └── sao/            # SAO Progressive 小说文本 (1-8卷)
├── data/               # 项目技术文档
├── docs/               # 项目文档
├── docker-compose.yml  # 容器编排
├── Makefile            # 构建命令
└── VERSION             # 当前版本
```

## 更新日志

### v0.200 (2026-04-06) - 小说知识库
- SAO Progressive 小说（1-8卷）向量化知识库（ChromaDB + BGE-small-zh-v1.5）
- 小说文本按章节 + 语义两级分块入库，携带基础结构和游戏世界两维度标注
- 新增 Makefile target: `ingest-novels` / `verify-vectordb`
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
