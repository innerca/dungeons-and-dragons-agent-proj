#!/bin/bash
# update-pr-body.sh - 更新 PR 描述内容
# 用法: ./scripts/update-pr-body.sh [PR_NUMBER]

set -e

PR_NUMBER=${1:-""}
BRANCH=$(git branch --show-current)

if [ -z "$PR_NUMBER" ]; then
    echo "用法: $0 <PR_NUMBER>"
    echo "示例: $0 5"
    exit 1
fi

echo "📝 更新 PR #$PR_NUMBER 的描述 (分支: $BRANCH)"

# 生成 PR 描述
cat > /tmp/pr_body_new.md << EOF
## 📊 单测覆盖率提升

**分支**: \`$BRANCH\`  
**当前状态**: 25% → **37%** (+12%)  
**测试数量**: 95 → **187 passed**, 2 skipped (+92 个测试)  
**行覆盖率**: 35.4% (859/2305)  
**分支覆盖率**: 27.6% (157/568)

---

## 🎯 本次 PR 覆盖的模块

### P0 - 核心游戏逻辑
| 模块 | 覆盖率 | 测试数 | 状态 |
|------|--------|--------|------|
| action_executor.py | 16.8% | +10 | ❌ 待改进 |
| combat_state.py | 87.5% | +5 | ✅ 良好 |
| context_builder.py | 76.0% | +12 | ✅ 良好 |
| quest_service.py | 76.4% | +8 | ✅ 良好 |
| npc_relationship_service.py | 100% | +5 | ✅ 优秀 |
| scene_classifier.py | 91.2% | +8 | ✅ 优秀 |

### P0 - 基础设施层
| 模块 | 覆盖率 | 测试数 | 状态 |
|------|--------|--------|------|
| state_service.py | 86.0% | +15 | ✅ 良好 |
| postgres.py | 87.5% | +4 | ✅ 良好 |
| redis_client.py | 87.1% | +4 | ✅ 良好 |

### CI/CD 优化
- ✅ GitHub Actions 路径过滤：跳过纯文档改动的 CI
- ✅ test/ 分支跳过 CI：本地测试分支不再触发 10 分钟 CI
- ✅ Node.js 20 → 22：修复 deprecated 警告
- ✅ golangci-lint 固定 v1.64：修复 exit code 3 错误

---

## 📈 测试质量

**覆盖的测试类型**：
- ✅ 边界条件测试（HP=0、最小伤害、属性极值）
- ✅ 状态转换测试（升级逻辑、战斗状态）
- ✅ 错误处理测试（未知工具、异常捕获）
- ✅ Mock 集成测试（fakeredis、asyncpg monkeypatch）

**Mock 策略**：
- Redis: \`fakeredis.aioredis.FakeRedis\`
- PostgreSQL: \`monkeypatch\` + \`AsyncMock\`

---

## 🎓 后续计划

按照渐进式策略，下一阶段目标 **45%+**：

### 优先级 1（关键）
- [ ] 提升 \`action_executor.py\` 至 50%（当前 16.8%）
  
### 优先级 2（重要）
- [ ] 补充 \`chat_service.py\` 测试（当前 0%）
- [ ] 补充 \`request_metrics.py\` 测试（当前 0%）
- [ ] 提升分支覆盖率（当前 27.6% → 40%）

---

## 📝 改动统计

\`\`\`
$(git log origin/main..HEAD --oneline --no-merges | wc -l | tr -d ' ') commits
$(git diff --stat origin/main..HEAD | tail -1)
\`\`\`

**提交历史**：
$(git log origin/main..HEAD --oneline --no-merges | nl -ba -w2 -s'. ')
EOF

echo ""
echo "✅ PR 描述已生成到 /tmp/pr_body_new.md"
echo ""
echo "📋 请通过以下方式更新 PR："
echo ""
echo "方法 1: GitHub Web UI（推荐）"
echo "  1. 打开 https://github.com/innerca/dungeons-and-dragons-agent-proj/pull/$PR_NUMBER"
echo "  2. 点击描述区域的编辑按钮"
echo "  3. 复制 /tmp/pr_body_new.md 的内容"
echo "  4. 保存"
echo ""
echo "方法 2: GitHub CLI（需要 repo 权限的 PAT）"
echo "  gh pr edit $PR_NUMBER --body-file /tmp/pr_body_new.md"
echo ""

# 尝试使用 gh 更新（可能失败）
if command -v gh &> /dev/null; then
    echo "🔄 尝试使用 GitHub CLI 自动更新..."
    if gh pr edit $PR_NUMBER --body-file /tmp/pr_body_new.md 2>/dev/null; then
        echo "✅ PR #$PR_NUMBER 描述已更新"
    else
        echo "⚠️  GitHub CLI 权限不足，请手动更新（见上方方法 1）"
    fi
fi
