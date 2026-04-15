# Engineering 文档索引

> 本目录包含项目的工程规范、代码质量检查、架构设计等技术文档。

---

## 🎯 快速导航

### 按角色查找

**开发者**：
- 日常开发 → [Claude模板](./claude_template.md)
- 代码提交前 → 对应语言的[专属审查规范](#-代码质量审查规范)
- 架构设计 → [Agent工程手册](./Agent工程手册final_version.md)

**技术负责人**：
- 代码审查标准 → [通用审查规范](./claude_quality_check_prompt.md)
- 团队规范制定 → 六语言[专属审查规范](#-代码质量审查规范)
- 工程师评估 → [工程题集](./题集.md)

**架构师**：
- 系统设计 → [Agent工程手册](./Agent工程手册final_version.md)
- 用户画像方案 → [简洁可拓展方案](./端侧用户画像系统：简洁可拓展落地方案.md) 或 [轻量级方案](./端侧轻量级用户画像系统落地方案.md)

---

## 📚 文档分类

### 🔍 代码质量审查规范

通用规范与六语言专属审查Prompt，用于AI代码审查和质量保证。

| 文档 | 说明 | 适用场景 |
|------|------|----------|
| [通用审查规范](./claude_quality_check_prompt.md) | R1-R11红线规则、量化标准、豁免机制 | 所有语言项目的基准规范 |
| [Java 专属审查](./quality_check_java.md) | 线程安全、InterruptedException、Optional、JPQL注入 | Java/Spring项目开发 |
| [Python 专属审查](./quality_check_python.md) | async阻塞检测、realpath异常降级、事务异步IO | Python/FastAPI/Django开发 |
| [Go 专属审查](./quality_check_go.md) | goroutine循环变量、err!=nil豁免、事务goroutine | Go微服务开发 |
| [TypeScript 专属审查](./quality_check_typescript.md) | Promise Rejection、同构环境差异、前端组件豁免 | TypeScript/React/Node.js开发 |
| [C++ 专属审查](./quality_check_cpp.md) | const正确性、lambda捕获、析构函数异常、RAII | C++系统开发 |
| [Rust 专属审查](./quality_check_rust.md) | unsafe SAFETY注释、FFI安全、Pin/Unpin、所有权 | Rust系统开发 |

**使用原则**：
1. 优先使用对应语言的专属Prompt（已包含通用规则）
2. 专属Prompt中的语言特有规则优先于通用规范
3. 通用规范作为基准参考，确保跨语言一致性

---

### 📘 开发规范与模板

项目开发的标准流程和模板文件。

| 文档 | 说明 | 用途 |
|------|------|------|
| [Claude模板](./claude_template.md) | AI辅助开发的工作流模板 | 规范AI助手的开发行为 |
| [Agent工程手册](./Agent工程手册final_version.md) | 完整版Agent工程实践指南 | 系统架构设计、最佳实践 |

---

### 🎓 工程题集

| 文档 | 说明 | 用途 |
|------|------|------|
| [工程题集](./题集.md) | 工程师能力评估题集 | 面试、自我学习、技能提升 |

---

### 🏗️ 架构设计文档

用户画像系统的设计方案。

| 文档 | 说明 | 特点 |
|------|------|------|
| [简洁可拓展方案](./端侧用户画像系统：简洁可拓展落地方案.md) | 轻量级、易落地的方案 | 适合快速迭代的项目 |
| [轻量级方案](./端侧轻量级用户画像系统落地方案.md) | 更详细的落地方案 | 包含完整的技术实现细节 |

---

## 📊 文档统计

- **总文档数**：12个
- **代码审查规范**：7个（1通用 + 6语言专属）
- **开发规范**：2个
- **架构设计**：2个
- **其他**：1个（题集）

---

## 🔄 更新记录

| 日期 | 更新内容 | 说明 |
|------|---------|------|
| 2026-04-15 | 初始创建 | 建立engineering目录索引 |

---

> 💡 **提示**：本文档为engineering目录的快速导航入口，详细内容请查阅对应文档。
