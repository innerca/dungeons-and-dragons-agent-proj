# 项目指标基线

## 状态

- 文档状态：`已完成首轮真实日志回填`
- 采集入口：`bash scripts/collect_metrics.sh <log-file>`
- 当前说明：下面这组数据来自 `2026-04-21` 的一段真实 GameServer 日志摘录，共整理出 `19` 条 `request_summary`。这不是严格控制变量下的压测结果，也不是线上 SLA，只能作为当前主链路的第一轮运行态基线。

## 首轮基线记录

| 采集日期 | 环境 | 样例数 | 模型 | 备注 |
|---|---|---|---|---|
| 2026-04-21 | Docker 内游戏服务，日志显示 `/app` 路径和容器内 Redis / PostgreSQL / ChromaDB 连接 | 19 | `deepseek-chat` | 用户提供的真实游玩日志摘录，覆盖开场、状态查询、移动、战斗、任务、NPC 对话 |

## 关键指标

| 指标 | 当前值 | 备注 |
|---|---|---|
| Avg total latency | `20641.97 ms` | 从 `request_summary total_ms` 手工汇总 |
| P50 total latency | `19870.60 ms` | 当前主链路中位数接近 `20s` |
| P95 total latency | `29405.80 ms` | 最慢样本接近 `29.4s` |
| Avg first token latency | `1297.75 ms` | 首 token 已进入 `1s` 量级 |
| P50 first token latency | `1299.80 ms` | 体感首屏中位数约 `1.3s` |
| P95 first token latency | `1752.20 ms` | 长上下文时会抬升 |
| Avg RAG latency | `88.96 ms` | 冷启动样本把尾部拉高 |
| RAG hit rate | `100%` | 这里只按 `rag_chunks > 0` 计算，不代表 `entities` 集合稳定命中 |
| Avg LLM latency | `11829.44 ms` | 当前总耗时主要被模型调用拉高 |
| Avg tool latency | `5.67 ms` | 工具本身不是主要时延瓶颈 |
| Avg input tokens | `7376.37` | 上下文规模已经不小 |
| Avg output tokens | `236.32` | 输出长度中等 |
| Avg LLM calls / request | `1.63` | 部分请求存在二次或三次调用 |
| Avg tool calls / request | `0.63` | 并非每轮都进入工具 |
| Avg successful tool calls / request | `0.42` | 来自 `tool_success_count` |
| Avg failed tool calls / request | `0.21` | 失败请求主要集中在少数异常场景 |
| Tool success rate | `66.67%` | 以成功 / 失败工具调用总数计算 |
| Stream success rate | `100%` | 这批日志里所有请求都完成了流式输出 |
| Fallback usage rate | `0%` | 这批样本没有触发 fallback |
| Avg estimated cost / request | `$0.001099` | 来自 `cost_usd` |
| Total estimated cost | `$0.020879` | 19 条样本合计 |
| Slow request alert rate | `100%` | `19/19` 都触发了 `slow_request_alert` |

## 这轮基线能说明什么

- `first_token_ms` 已经稳定在 `1s` 到 `1.8s` 区间，说明 `WebSocket -> gRPC -> SSE` 主链路的首屏响应已经可用。
- `total_ms` 仍然普遍落在 `14s` 到 `29s`，瓶颈主要在 `llm_ms`，而不是 RAG 或工具执行。
- 工具执行耗时很低，但工具失败并不低，说明当前更大的问题是工具正确性和业务边界，而不是工具性能。
- `fallback_used=0` 只能说明这批样本没打到降级路径，不能说明 fallback 已经被实测验证。

## 这轮基线里的异常说明

- `rag_chunks=3` 的命中率是 `100%`，但日志里多次出现 `collection=entities status=empty`，所以当前只能说“小说分块检索有结果”，不能说“双路知识都稳定命中”。
- `P95 RAG latency` 会被冷启动样本显著拉高；服务启动期有 Chroma 初始化和嵌入模型加载，不应和纯热启动样本混在一起做结论。
- `slow_request_alert` 全量触发，说明当前 `5000ms` 阈值对这条链路区分度不够，后续要么拆分场景阈值，要么继续优化上下文和模型调用成本。

## 后续回填规则

- 下一轮优先用固定样例集重新跑一遍，并直接保留脚本原始输出。
- 如果环境、provider、模型或数据集范围变化较大，应新增一轮记录，不直接覆盖这次结果。
- `fallback`、流式中断、gRPC 失败这类未在本轮出现的场景，要单独补验证结果，而不是从这份基线里倒推。

## 当前已知静态基线

这部分不是运行态指标，但可以作为当前仓库的静态工程基线保留：

| 项目 | 当前记录 |
|---|---|
| Python GameServer 测试 | `241 passed` |
| Python 行覆盖率 | `52.30%` |
| Python 分支覆盖率 | `50%` |
| Go Gateway 语句覆盖率 | `41.4%` |

## 后续采集建议

后续每一轮采集都建议同时记录：

1. 固定样例集列表。
2. 使用的模型和 provider。
3. 是否在本地开发模式还是 Docker 模式下运行。
4. 是否启用完整小说数据或仅使用 demo 数据。
5. 原始日志文件路径或日志摘要。

## 回填规则

- 只回填脚本输出的真实结果。
- 旧日志如果没有 `first_token_ms`，该列保持“不可用”，不要补算。
- 如环境、模型或样例集变化较大，应新增一轮采集记录，而不是直接覆盖旧数据。
