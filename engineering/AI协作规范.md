
## 一键安装

echo "✅ 开始安装 AI 协作规范..."
mkdir -p .ai

---

echo '# AI 协作规范

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
生成 Python 代码时读取 `.ai/python-style.md`' > CLAUDE.md

---

echo '# AI 输出模板

## Plan 模板（等确认）
```
[模式: Plan]
### 环境：分支、未提交、远端
### 子任务：[动作] [路径] — [目的]
### 回滚：`git reset --hard HEAD~1`
**请回复"执行"**
```

## L1 模板（直行）
```
[模式: L1]
### 调用链：谁调我 / 我调谁
### 破坏签名？[是/否]
### 边界：[null/超时/竞态]
```

## 审计（附代码尾）
```
- [ ] 硬编码？ 破坏签名？ 新env？ 冗余文件？
```' > .ai/templates.md

---

echo '# Python 风格速查

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
```' > .ai/python-style.md

---

echo "✅ AI 协作规范已安装完成！"

echo ""
echo "搞定。现在 AI 会先思考，再编码。"
