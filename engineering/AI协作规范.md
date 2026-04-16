# AI 协作规范

> 让 AI 像资深工程师一样思考，先规划后编码，先审计后交付。  
> **零配置，复制即用。**

---

## 一键安装

复制以下命令到终端执行，自动创建所有规范文件：

```bash
mkdir -p .ai

cat > CLAUDE.md << 'EOF'
# AI 协作规范

## 模式自判（首行声明 `[模式: X]`）
- Plan：≥2文件 / 命令 / 依赖变更 → 等确认
- L1：单文件核心逻辑 → 直行
- L2：文案/样式/注释 → 直行

## 铁律
1. 禁硬编码 URL/密钥/魔法数字 → 用 env
2. 禁 `lint --fix .`
3. Plan 未确认不写操作
4. 同错 ≥3 次 → 停

## 模板
触发 Plan/L1 时读取 `.ai/templates.md`
生成 Python 代码时读取 `.ai/python-style.md`
EOF

cat > .ai/templates.md << 'EOF'
# AI 输出模板

## Plan 模板(等确认)
```
[模式: Plan]
### 环境:分支、未提交、远端
### 子任务:[动作] [路径] — [目的]
### 回滚:`git reset --hard HEAD~1`
**请回复"执行"**
```

## L1 模板(直行)
```
[模式: L1]
### 调用链:谁调我 / 我调谁
### 破坏签名?[是/否]
### 边界:[null/超时/竞态]
```

## 审计(附代码尾)
```
- [ ] 硬编码? 破坏签名? 新env? 冗余文件?
```
EOF

cat > .ai/python-style.md << 'ENDOFFILE'
# Python 风格速查

```python
# 早返回
def process(data: dict) -> dict | None:
    if not data or not data.get("valid"):
        return None
    ...

# 不可变
def update(cfg: dict) -> dict:
    return {**cfg, "timeout": 30}

# 依赖注入
class Reporter:
    def __init__(self, cache, notifier):
        self.cache = cache
        self.notifier = notifier
```
ENDOFFILE

echo "✅ AI 协作规范已安装。"
```

---

## 安装后目录结构

```
你的项目/
├── CLAUDE.md          # AI 每次自动加载的核心规范
└── .ai/
    ├── templates.md   # 详细模板（触发 Plan/L1 时自动读取）
    └── python-style.md # Python 范例（生成 Python 代码时参考）
```

---

## 三种模式速览

| 模式 | 触发条件 | AI 行为 | 首行声明 |
| :--- | :--- | :--- | :--- |
| **Plan** | 多文件 / 命令 / 依赖变更 | 输出规划书，**等你确认** | `[模式: Plan]` |
| **L1** | 单文件核心逻辑变更 | 输出思考报告，直接执行 | `[模式: L1]` |
| **L2** | 文案/样式/注释微调 | 单行说明，直接执行 | `[模式: L2]` |

---

## 效果示例

### Plan 模式(等待确认)

```text
[模式: Plan]
### 环境:feature/user-cache,无未提交
### 子任务:
1. 修改 src/cache.ts — 增加过期时间
**请回复"执行"**
```

### L1 模式(直接执行)

```text
[模式: L1]
### 调用链:被 3 个组件调用
### 破坏签名?否
[代码...]
```

### L2 模式(极简)

```text
[模式: L2]
// [AI] 调整按钮间距
[代码...]
```

---

## 自定义与扩展

| 需求 | 操作 |
| :--- | :--- |
| 调整模式触发规则 | 编辑 `CLAUDE.md` |
| 修改 Plan/L1 模板 | 编辑 `.ai/templates.md` |
| 增加其他语言范例 | 在 `.ai/` 下新建 `java-style.md` 等，并在 `CLAUDE.md` 中引用 |

---

## 卸载

```bash
rm CLAUDE.md && rm -rf .ai/
```

---

**搞定。现在 AI 会先思考,再编码。**
