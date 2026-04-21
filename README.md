# Dungeons & Dragons Agent 系统项目

这是一个用 DND / SAO 场景承载的 Agent 应用后端项目。题材本身只是交互外壳，核心目标是验证多轮对话、状态推进、工具调用、RAG 检索、流式返回和可观测性这一整条链路。

项目现在已经把一条完整链路跑通了：前端发起请求，Gateway 转成 gRPC 调到 GameServer，GameServer 组装上下文、调用模型、执行工具、写回状态，再把结果流式返回前端。

## Demo

- Demo 视频：[demo-gameplay.mp4](./demo-gameplay.mp4)
- 可直接看这几个片段：
  - `00:00` 注册 / 登录
  - `00:15` 角色创建
  - `00:30` 进入游戏与开场对话
  - `01:00` 状态查询与菜单交互
  - `01:45` 探索、移动与 NPC / 任务交互
  - `03:00` Prompt 注入演示
  - `04:00` 战斗与技能调用

视频里已经覆盖注册、登录、角色创建、探索、战斗和 Prompt 注入演示。

## 系统组成

- `frontend`
  React + TypeScript 前端，负责登录、注册、角色创建和游戏界面。
- `gateway`
  Go 网关，负责 HTTP API、WebSocket、SSE 和 gRPC 桥接。
- `gameserver`
  Python 服务，负责上下文组装、RAG 检索、模型调用、工具执行和状态写回。
- `postgres / redis / chromadb`
  分别负责持久化、缓存和检索数据。

## 现在有些什么

下面这张表只区分当前仓库里的实现情况，不写未来规划。

| 模块 | 状态 | 说明 |
|---|---|---|
| 上下文组装 | `部分实现` | 已有状态快照、摘要、RAG 结果和最近消息拼装 |
| 工具调用 | `已实现基础版` | 已有 ReAct 循环、参数解析、工具执行和状态写回 |
| 流式链路 | `已实现基础版` | 已打通 `WebSocket -> gRPC -> SSE` |
| 可观测性 | `部分实现` | 已有 `trace_id`、请求耗时、token 和成本估算 |
| 降级与熔断 | `部分实现` | 已有重试、三态熔断和 fallback provider |
| 安全边界 | `部分实现` | 已有 `player_id` 注入、工具参数校验和演示样例 |
| 测试与评估 | `部分实现` | 单元测试和覆盖率有了，系统级评测还没补齐 |

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

主链路大致是这样：

`Frontend -> Gateway -> GameServer -> LLM / Tool -> State Update -> Stream Back`

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

会初始化：

- PostgreSQL 表结构
- Demo 账号和角色数据
- 装备、任务进度、NPC 关系等示例数据
- ChromaDB 示例检索块

测试账号：

- `demo / demo123`
- `testplayer / test123`

需要清空重来时：

```bash
make init-data-reset
```

`asset/sao/` 里的完整小说文本不是启动必需项。没有这部分数据也能用 demo 数据把链路跑起来。

## 本地开发

环境要求：

- Go `1.22+`
- Python `3.12+`
- Node.js `18+`
- `uv`
- `protoc`
- `protoc-gen-go`
- `protoc-gen-go-grpc`

启动命令：

```bash
make proto-gen
make dev-gameserver
make dev-gateway
make dev-frontend
```

Docker 模式：

```bash
make start-docker
make dev-logs
```

## 测试

Python GameServer：

```bash
cd gameserver
uv run pytest tests/ -v
uv run pytest tests/ --cov=src/gameserver --cov-branch
```

Go Gateway：

```bash
cd gateway
GO111MODULE=on go test ./... -v
GO111MODULE=on go test ./... -coverprofile=coverage.out
go tool cover -html=coverage.out -o coverage.html
```

仓库里当前记录的测试基线：

- Python GameServer：`241 passed`
- Python 行覆盖率：`52.30%`
- Python 分支覆盖率：`50%`
- Go Gateway 语句覆盖率：`41.4%`

这些数字只说明当前代码测试情况，不代表系统级效果评测。

## 运行态指标

GameServer 现在会在 `request_summary` 日志里记录：

- `total_ms`
- `first_token_ms`
- `rag_ms`
- `llm_ms`
- `tool_ms`
- `rag_chunks`
- `input_tokens`
- `output_tokens`
- `cost_usd`
- `llm_calls`
- `tool_calls`
- `tool_success_count`
- `tool_failure_count`
- `stream_success`
- `fallback_used`

日志聚合入口：

```bash
make collect-metrics LOG_FILE=path/to/gameserver.log
```

如果你是跑 Docker，也可以直接把日志管道给脚本：

```bash
docker compose logs --no-color gameserver | bash scripts/collect_metrics.sh -
```

已补出的运行证据：

- 首轮真实日志基线：[engineering/project/project-metrics-baseline-cn.md](./engineering/project/project-metrics-baseline-cn.md)
- 已知失败模式记录：[engineering/project/failure-modes-cn.md](./engineering/project/failure-modes-cn.md)

## 代码位置

几个关键文件：

- `gameserver/src/gameserver/game/context_builder.py`
  负责系统提示、玩家状态、任务 / 战斗 / 关系信息、摘要和 RAG 结果拼装。
- `gameserver/src/gameserver/service/chat_service.py`
  负责场景分类、RAG 检索、ReAct 循环、工具调用和流式返回。
- `gameserver/src/gameserver/game/action_executor.py`
  负责具体工具执行和状态变更。
- `gateway/internal/handler/websocket.go`
  负责接收请求、生成 `trace_id`、启动 gRPC 流。
- `gateway/internal/handler/sse.go`
  负责把流式结果转成 SSE 返回前端。
- `gameserver/src/gameserver/service/request_metrics.py`
  负责请求级指标统计。
- `gameserver/src/gameserver/llm/circuit_breaker.py`
  负责熔断和 fallback。

## 文档入口

- [data/dnd-game-system.md](./data/dnd-game-system.md)
- [data/dnd-world-setting.md](./data/dnd-world-setting.md)
- [data/dnd-novel-chunking.md](./data/dnd-novel-chunking.md)
- [agent-engineering-handbook.md](./agent-engineering-handbook.md)
- [engineering/Agent工程手册final_version.md](./engineering/Agent工程手册final_version.md)
- [engineering/AI协作规范.md](./engineering/AI协作规范.md)

## 检索知识库

项目使用 ChromaDB 保存 SAO Progressive 文本分块和实体数据，用于 RAG。

本地数据路径预期为：

- `asset/sao/`

相关命令：

```bash
make ingest-novels
make verify-vectordb
```

## 后续还要补的部分

接下来更值得做的还是三件事：

1. 跑一轮固定样例，把运行态指标填成基线。
2. 补流式中断、工具失败、状态写回失败这些异常场景的记录。
3. 把 Prompt 注入和安全边界整理成更清楚的验证结果。

## 许可证

本项目采用 [CC BY-NC-ND 4.0](./LICENSE) 许可证。
