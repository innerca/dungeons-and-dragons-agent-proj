# Dungeons & Dragons Agent Project

一个基于微服务架构实现的 D&D 风格文字游戏原型。项目以《刀剑神域 Progressive》为世界观素材，结合 LLM、工具调用和本地检索，实现带状态管理的多轮游戏交互。

## 项目简介

当前项目由四部分组成：

- `frontend`：React + TypeScript 前端
- `gateway`：Go 网关，负责 HTTP、SSE、WebSocket 和 gRPC 桥接
- `gameserver`：Python 游戏服务，负责状态管理、工具执行、对话编排
- `postgres / redis / chromadb`：持久化、缓存和检索

项目的重点不在单次问答，而在一条完整的游戏链路：

- 玩家登录和创建角色
- 根据当前状态组装上下文
- 调用 LLM 生成行动决策
- 执行工具并更新角色 / 战斗 / 任务状态
- 将结果流式返回前端

## Demo

- 演示视频：[demo-gameplay.mp4](./demo-gameplay.mp4)

## 当前状态

已完成的部分：

- Frontend、Gateway、GameServer 的基础联通
- 角色、战斗、任务、NPC 关系、世界标记等核心状态
- ReAct + Function Calling 的主流程
- PostgreSQL、Redis、ChromaDB 集成
- Demo 数据初始化和 Docker 启动流程
- Python 和 Go 两侧基础测试

当前还在继续完善的部分：

- 流式链路的取消、重连、异常收尾
- 状态持久化的一致性边界
- 鉴权和安全边界
- 部分服务层逻辑的拆分

## 架构

```text
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
│                                                          (嵌入式 / 本地)
└──────────────────────────────────────────────────────────────────────┘
```

请求主链路：

`Frontend -> Gateway -> GameServer -> LLM / Tool Execution -> State Update -> Stream Back To Client`

## 快速开始

```bash
git clone https://github.com/innerca/dungeons-and-dragons-agent-proj.git
cd dungeons-and-dragons-agent-proj
cp .env.example .env
make init-data
make start
```

启动后访问：

- Docker 模式：`http://localhost:3000`
- 本地前端开发模式：`http://localhost:5173`

停止服务：

```bash
make stop
```

## 数据初始化

首次启动执行：

```bash
make init-data
```

初始化内容包括：

- PostgreSQL 表结构
- Demo 账号和玩家数据
- 装备、任务进度、NPC 关系等示例数据
- ChromaDB 示例检索块

测试账号：

- `demo / demo123`
- `testplayer / test123`

如果需要强制重置：

```bash
make init-data-reset
```

说明：

- `asset/sao/` 中的完整原文数据不是启动必需项
- 即使没有完整小说文本，仓库也可以使用 Demo 数据完成本地运行和联调

## 启动方式

### Docker 启动

```bash
make init-data
make start-docker
```

常用命令：

```bash
make stop
make dev-logs
```

### 本地开发

环境要求：

- Go `1.22+`
- Python `3.12+`
- Node.js `18+`
- `uv`
- `protoc`
- `protoc-gen-go`
- `protoc-gen-go-grpc`

分别在不同终端启动：

```bash
make proto-gen
make dev-gameserver
make dev-gateway
make dev-frontend
```

## 测试

### Python GameServer

```bash
cd gameserver
uv run pytest tests/ -v
uv run pytest tests/ --cov=src/gameserver --cov-branch
```

### Go Gateway

```bash
cd gateway
GO111MODULE=on go test ./... -v
GO111MODULE=on go test ./... -coverprofile=coverage.out
go tool cover -html=coverage.out -o coverage.html
```

## 本地验证

已在 `2026-04-21` 本地验证通过：

- `frontend`：`npm run build`
- `frontend`：`npm run lint`
- `gameserver`：`uv run pytest tests/ -q`，`241 passed`
- `gateway`：`GO111MODULE=on go test ./...`

## 技术栈

| 模块 | 技术 |
|------|------|
| 前端 | React + TypeScript + Vite |
| 网关 | Go + chi |
| 游戏服务器 | Python + grpcio |
| 客户端流式通信 | WebSocket + SSE |
| 服务间通信 | gRPC |
| 持久化 | PostgreSQL 16 + Redis 7 |
| 检索 | ChromaDB + BGE-small-zh |
| 容器化 | Docker Compose |
| Python 包管理 | uv |
| LLM 提供方 | 默认 DeepSeek |

## 设计文档

核心文档：

- [data/dnd-game-system.md](./data/dnd-game-system.md)：游戏系统蓝图
- [data/dnd-world-setting.md](./data/dnd-world-setting.md)：世界观设定
- [data/dnd-novel-chunking.md](./data/dnd-novel-chunking.md)：小说分块规则
- [agent-engineering-handbook.md](./agent-engineering-handbook.md)：与当前项目直接相关的 Agent 设计笔记

补充材料：

- [engineering/Agent工程手册final_version.md](./engineering/Agent工程手册final_version.md)
- [engineering/端侧轻量级用户画像系统落地方案.md](./engineering/端侧轻量级用户画像系统落地方案.md)

## 检索知识库

项目使用 ChromaDB 存储从 SAO Progressive 文本中切分出的本地知识块，用于 RAG 检索。

本地数据源路径预期为：

- `asset/sao/`

构建和校验命令：

```bash
make ingest-novels
make verify-vectordb
```

## 仓库结构

```text
.
├── frontend/           # React + TypeScript 前端
├── gateway/            # Go 网关
├── gameserver/         # Python 游戏服务与 Agent 编排
├── proto/              # gRPC 协议定义
├── data/               # 世界观、规则、实体和分块文档
├── engineering/        # 补充设计与研究文档
├── docs/               # 仓库整理和求职相关文档
├── scripts/            # 启动、初始化和辅助脚本
├── docker-compose.yml  # 本地编排
├── Makefile            # 常用命令
└── VERSION             # 项目版本
```

## 后续改进方向

当前更值得继续投入的方向：

1. 强化流式链路的取消、重连、清理和异常收尾
2. 收紧状态持久化的一致性边界和异常恢复
3. 拆分 GameServer 中偏大的编排逻辑
4. 明确鉴权与安全边界
5. 继续压缩文档层级，减少和实现无关的干扰信息

## 更新日志

### v0.5007 (2026-04-15)

- 在 README 中补充 Gateway 测试覆盖摘要
- 更新内部文档链接和锚点

### v0.5006 (2026-04-14)

- 提升 GameServer 核心模块测试覆盖率
- 扩展 `action_executor.py` 和 `quest_service.py` 测试

### v0.5005 (2026-04-14)

- 强化 CI 覆盖率检查和测试质量

### v0.5004 (2026-04-14)

- 为核心游戏模块补充更完整的测试覆盖

### v0.5003 (2026-04-14)

- 修复 Python、Go 和前端侧的代码质量问题

### v0.5002 (2026-04-14)

- 增加测试覆盖与 Demo 数据初始化

### v0.5001 (2026-04-13)

- 增加可观测性和 LLM 熔断降级

### v0.500 (2026-04-06)

- 引入数据驱动游戏引擎和 RAG 集成

### v0.400 (2026-04-06)

- 重构为全栈 D&D 游戏架构

### v0.300 (2026-04-06)

- 增加 D&D 游戏设计文档

### v0.200 (2026-04-06)

- 增加小说向量知识库支持

### v0.100 (2026-04-06)

- 初始版本发布

## 许可证

本项目采用 [CC BY-NC-ND 4.0](./LICENSE) 许可证。
